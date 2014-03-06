"""
Student autograder utilities.

This file provides a common interface for the CS 61A project
student-side autograder. Students do not need to read or understand
the contents of this file.

Usage:
This file is intended to run as the main script. Test cases should
be defined in two files:

* locked_tests.py
* unlocked_tests.py

This file supports the following primary options:

* Unlocking tests (-u): Students will receive test cases in locked
    form. Test cases can be unlocked by using the "-u" flag. Once a
    test is unlocked, students will be able to run the autograder with
    those cases (see below)
* Testing individual questions (-q): Students can test an individual
    question using the "-q" flag. Omitting the "-q" flag will test
    all unlocked test cases. By default, the autograder will stop once
    the first error is encountered (see below)
* Testing all questions regardless of errors (-a): When specified, the
    autograder continues running even if it encounters errors. The
    "-a" flag works even if the "-q" is used
* Interactive debugging (-i): by default, when the autograder
    encounters an error, it prints the stack trace and terminates. The
    "-i" will instead print the stack trace, then open an interactive
    console to allow students to inspect the environment.
"""

import argparse
from code import InteractiveConsole
import hmac
import pickle
import rlcompleter
import re
import traceback
import urllib.request
import os

__version__ = '1.0'

#############
# Utilities #
#############

class TestException(Exception):
    """Custom exception for autograder."""

    def __init__(self, test_src, outputs, explanation='', preamble='',
                 timeout=None):
        super().__init__()
        self.test_src = test_src
        self.outputs = outputs
        self.explanation = explanation
        self.preamble = preamble
        self.timeout=timeout

def underline(line, under='='):
    """Underlines a given line with the specified under style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style

    RETURNS:
    str; the underlined version of line
    """
    return line + '\n' + under * len(line)

def display_prompt(line, prompt='>>> '):
    """Formats a given line as if it had been typed in an interactive
    interpreter.

    PARAMETERS:
    line   -- object; represents a line of Python code. If not a
              string, line will be converted using repr. Otherwise,
              expected to contain no newlines for aesthetic reasons
    prompt -- str; prompt symbol. If a space is desired between the
              symbol and input, prompt must contain the space itself
    RETURNS:
    str; the formatted version of line
    """
    if type(line) != str:
        line = repr(line)
    return prompt + line


class TimeoutError(Exception):
    _message = 'Evaluation timed out!'

    def __init__(self, timeout):
        super().__init__(self)
        self.timeout = timeout

TIMEOUT = 10
def timed(fn, args=(), kargs={}, timeout=TIMEOUT):
    """Evaluates expr in the given frame.

    PARAMETERS:
    expr  -- str; Python expression to be evaluated
    frame -- dict; environment in which expr should be evaluated
    """
    from threading import Thread
    class ReturningThread(Thread):
        """Creates a daemon Thread with a result variable."""
        def __init__(self):
            Thread.__init__(self)
            self.daemon = True
            self.result = None
            self.error = None
        def run(self):
            try:
                self.result = fn(*args, **kargs)
            except Exception as e:
                e._message = traceback.format_exc(limit=2)
                self.error = e
    submission = ReturningThread()
    submission.start()
    submission.join(timeout)
    if submission.is_alive():
        raise TimeoutError(timeout)
    if submission.error is not None:
        raise submission.error
    return submission.result

#####################
# Testing Mechanism #
#####################

PS1 = '>>> '
PS2 = '... '

def get_name(test):
    return test['name'] if type(test['name'])==str else test['name'][0]

def run(test, global_frame=None, interactive=False):
    """Runs all test suites for this class.

    PARAMETERS:
    test         -- dict; test cases for a single question
    global_frame -- dict; bindings for the global frame
    interactive  -- bool; True if interactive mode is enabled

    DESCRIPTION:
    Test suites should be correspond to the key 'suites' in test.
    If no such key exists, run as if zero suites are
    defined. Use the first value corresponding to the key 'name' in
    test as the name of the test.

    RETURNS:
    bool; True if all suites passed.
    """
    name = get_name(test)
    print(underline('Test ' + name))
    if global_frame is None:
        global_frame = {}
    if 'note' in test:
        print('\n'.join(process_input(test['note'])))
    if 'suites' not in test:
        test['suites'] = []
    if 'cache' in test:
        test['cache'](global_frame)

    preamble = ''
    if 'preamble' in test and 'all' in test['preamble']:
        preamble += test['preamble']['all']
    postamble = ''
    if 'postamble' in test and 'all' in test['postamble']:
        postamble += test['postamble']['all']

    passed = 0
    for counter, suite in enumerate(test['suites']):
        # Preamble and Postamble
        new_preamble = preamble
        if 'preamble' in test:
            new_preamble += test['preamble'].get(counter, '')
        new_postamble = postamble
        if 'postamble' in test:
            new_postamble += test['postamble'].get(counter, '')
        new_postamble = compile('\n'.join(process_input(new_postamble)),
                  '{} suite {} postamble'.format(name, counter),
                  'exec')
        # Run tests
        try:
            run_suite(new_preamble, suite, global_frame.copy(),
                      '{} suite {}'.format(name, counter))
        except TestException as e:
            exec(new_postamble, global_frame.copy())
            failed = handle_failure(e, counter + 1,
                                       global_frame.copy(),
                                       interactive)
            assert failed, 'Autograder error'
            break
        else:
            passed += 1
        finally:
            exec(new_postamble, global_frame.copy())
    total_cases = 0
    for suite in test['suites']:
        total_cases += len(suite)
    if passed == len(test['suites']):
        print('All unlocked tests passed!')
    if test['total_cases'] and total_cases < test['total_cases']:
        print('Note: {} still has {} locked cases.'.format(
                name,
                test['total_cases'] - total_cases))
    print()
    return passed == len(test['suites'])

def run_suite(preamble, suite, global_frame, label):
    """Runs tests for a single suite.

    PARAMETERS:
    preamble     -- str; the preamble that should be run before
                    every test
    suite        -- list; each element is a test case, represented
                    as a 2-tuple or 3-tuple
    global_frame -- dict; global frame

    DESCRIPTION:
    Each test case in the parameter suite is represented as a
    2-tuple or a 3-tuple:

        (input, outputs)
        (input, outputs, explanation)

    where:
    input       -- str; a (possibly multiline) string of Python
                   source code
    outputs     -- iterable or string; if string, outputs is the
                   sole expected output. If iterable, each element
                   in outputs should correspond to an input slot
                   in input (delimited by '$ ').
    explanation -- (optional) str; an explanation for the test

    For each test, a new frame is created and houses all bindings
    made by the test. The preamble will run first (if it exists)
    before the test input.

    Expected output and actual output is tested on shallow equality
    (==). If a test fails, a TestException will be raised that
    contains information about the test.

    RAISES:
    TestException; contains information about the test that failed.
    """
    new_preamble = compile('\n'.join(process_input(preamble)),
                       '{} preamble'.format(label), 'exec')
    exec(new_preamble, global_frame)

    for test, outputs, *explanation in suite:
        frame = global_frame.copy()
        if type(outputs) == str:
            outputs = (outputs,)
        out_iter = iter(outputs)

        lines = process_input(test)
        current, prompts = '', 0
        for i, line in enumerate(lines):
            if line.startswith('$ ') or \
                    (i == len(lines) - 1 and prompts == 0):
                prompts += 1
                try:
                    exec(current, frame)
                except:
                    raise TestException(test, outputs, explanation,
                                        preamble)
                current = ''
                output = next(out_iter)
                expect = eval(output, frame)
                try:
                    actual = timed(eval, (line.lstrip('$ '), frame))
                except:
                    raise TestException(test, outputs, explanation,
                                        preamble)

                if expect != actual:
                    if explanation:
                        explanation = explanation[0]
                    else:
                        explanation = ''
                    raise TestException(test, outputs, explanation,
                                        preamble)
            else:
                current += line + '\n'
        if prompts == 0:
            output = next(out_iter)
            expect = eval(output, frame)
            actual = eval(line.lstrip('$ '), frame)
            if expect != actual:
                if explanation:
                    explanation = explanation[0]
                else:
                    explanation = ''
                raise TestException(test, outputs, explanation,
                                    preamble)

def handle_failure(error, suite, global_frame, interactive):
    """Handles a test failure.

    PARAMETERS:
    error        -- TestException; contains information about the
                    failed test
    suite        -- int; suite number (for informational purposes)
    global_frame -- dict; global frame
    interactive  -- bool; True if interactive mode is enabled

    DESCRIPTION:
    Expected output and actual output are checked with shallow
    equality (==).

    RETURNS:
    bool; True if error actually occurs, which should always be
    the case -- handle_failure should only be called if a test
    fails.
    """
    print(underline('Test case failed:'.format(suite), under='-'))
    console = InteractiveConsole(locals=global_frame)
    incomplete = False
    for line in process_input(error.preamble):
        if not incomplete and not line:
            incomplete = False
            continue
        prompt = PS2 if incomplete else PS1
        print(display_prompt(line, prompt))
        incomplete = console.push(line)

    incomplete = False
    outputs = iter(error.outputs)
    lines = process_input(error.test_src)
    prompts = 0
    for i, line in enumerate(lines):
        if line.startswith('$ ') or \
                (i == len(lines) - 1 and prompts == 0):
            line = line.lstrip('$ ')
            prompt = PS2 if incomplete else PS1
            print(display_prompt(line, prompt))

            expect = eval(next(outputs), global_frame.copy())
            try:
                actual = timed(eval, (line, global_frame.copy()))
            except RuntimeError:
                print('# Error: maximum recursion depth exceeded')
                if interactive:
                    interact(console)
                print()
                return True
            except TimeoutError as e:
                print('# Error: evaluation exceeded {} seconds'.format(e.timeout))
                return True
            except Exception as e:
                console.push(line)
                print('# Error: expected', repr(expect), 'got',
                      e.__class__.__name__)
                if interactive:
                    interact(console)
                print()
                return True

            print(display_prompt(actual, prompt=''))
            if expect != actual:
                print('# Error: expected', repr(expect), 'got', repr(actual))
                if interactive:
                    interact(console)
                print()
                return True
            incomplete = False
        else:
            if not incomplete and not line:
                incomplete = False
                continue
            prompt = PS2 if incomplete else PS1
            print(display_prompt(line, prompt))
            incomplete = console.push(line)
    print()
    return False

def interact(console):
    """Starts an interactive console."""
    console.interact('# Interactive console\n'
                     '# Type exit() to quit')

def process_input(src):
    """Splits a (possibly multiline) string of Python input into
    a list, adjusting for common indents.

    PARAMETERS:
    src -- str; (possibly) multiline string of Python input

    DESCRIPTION:
    Indentation adjustment is determined by the first nonempty
    line. The characters of indentation for that line will be
    removed from the front of each subsequent line.

    RETURNS:
    list of strings; lines of Python input
    """
    src = src.lstrip('\n').rstrip()
    match = re.match('\s+', src)
    if match:
        length = len(match.group(0))
    else:
        length = 0
    return [line[length:] for line in src.split('\n')]

##########################
# Command Line Interface #
##########################

def run_preamble(preamble, frame):
    """Displays the specified preamble."""
    console = InteractiveConsole(frame)
    incomplete = False
    for line in process_input(preamble):
        if not incomplete and not line:
            incomplete = False
            continue
        prompt = PS2 if incomplete else PS1
        print(display_prompt(line, prompt))
        incomplete = console.push(line)

def get_test(tests, question):
    """Retrieves a test for the specified question in the given list
    of tests.

    PARAMETERS:
    tests    -- list of dicts; list of tests
    quesiton -- str; name of test

    RETURNS:
    dict; the test corresponding to question. If no such test is found,
    return None
    """
    for test in tests:
        if 'name' not in test:
            continue
        names = test['name']
        if type(names) == str:
            names = (names,)
        if question in names:
            return test

def unlock(question, locked_tests, unlocked_tests):
    """Unlocks a question, given locked_tests and unlocked_tests.

    PARAMETERS:
    question       -- str; the name of the test
    locked_tests   -- module; contains a list of locked tests
    unlocked_tests -- module; contains a list of unlocked tests

    DESCRIPTION:
    This function incrementally unlocks all cases in a specified
    question. Students must answer in the order that test cases are
    written. Once a test case is unlocked, it will remain unlocked.

    Persistant state is stored by rewriting the contents of
    locked_tests.py and unlocked_tests.py. Students should NOT manually
    change these files.
    """
    hash_key = locked_tests['hash_key']
    imports = unlocked_tests['project_info']['imports']

    locked = get_test(locked_tests['tests'], question)
    unlocked = get_test(unlocked_tests['tests'], question)
    name = get_name(locked)

    prompt = '?'
    print(underline('Unlocking tests for {}'.format(name)))
    print('At each "{}", type in what you would expect the output to be if you had implemented {}'.format(prompt, name))
    print('Type exit() to quit')
    print()

    global_frame = {}
    for line in imports:
        exec(line, global_frame)

    has_preamble = 'preamble' in locked
    if has_preamble and 'all' in locked['preamble']:
        run_preamble(locked['preamble']['all'], global_frame)

    def hash_fn(x):
        return hmac.new(hash_key.encode('utf-8'),
                        x.encode('utf-8')).digest()

    if 'suites' not in locked:
        return
    for suite_num, suite in enumerate(locked['suites']):
        assert suite_num <= len(unlocked['suites']), 'Incorrect number of suites'
        if not suite:
            continue
        if has_preamble and suite_num in locked['preamble']:
            run_preamble(locked['preamble'][suite_num],
                         global_frame.copy())
            unlocked.setdefault('preamble', {})[suite_num] = locked['preamble'][suite_num]
        while suite:
            case = suite[0]
            lines = [x.strip() for x in case[0].split('\n')
                     if x.strip() != '']
            answers = []
            outputs = case[1]
            if type(outputs) not in (list, tuple):
                outputs = [outputs]
            output_num = 0
            for line in lines:
                if len(lines) > 1 and not line.startswith('$'):
                    print(">>> " + line)
                    continue
                line = line.lstrip('$ ')
                print(">>> " + line)
                correct = False
                while not correct:
                    try:
                        student_input = input(prompt + ' ')
                    except (KeyboardInterrupt, EOFError):
                        try:
                            print('\nExiting unlocker...')
                        # When you use Ctrl+C in Windows, it throws
                        # two exceptions, so you need to catch both of
                        # them.... aka Windows is terrible.
                        except (KeyboardInterrupt, EOFError):
                            pass
                        return
                    if student_input in ('exit()', 'quit()'):
                        print('\nExiting unlocker...')
                        return
                    correct = hash_fn(student_input) == outputs[output_num]
                    if not correct:
                        print("Not quite...try again!")
                answers.append(student_input)
                output_num += 1
            case[1] = answers
            if len(unlocked['suites']) == suite_num:
                unlocked['suites'].append([case])
            else:
                unlocked['suites'][-1].append(case)
            suite.pop(0)

            print("Congratulations, you have unlocked this case!")

    print("You have unlocked all of the tests for this question!")

def check_for_updates(remote, version):
    print('You are running version', version, 'of the autograder')
    try:
        url = os.path.join(remote, 'autograder.py')
        data = timed(urllib.request.urlopen, (url,), timeout=2)
        contents = data.read().decode('utf-8')
    except (urllib.error.URLError, urllib.error.HTTPError):
        print("Couldn't check remote autograder")
        return False
    except TimeoutError:
        print("Checking for updates timed out.")
        return False
    remote_version = re.search("__version__\s*=\s*'(.*)'",
                               contents)
    if remote_version and remote_version.group(1) != version:
        print('Version', remote_version.group(1), 'is available.')
        prompt = input('Do you want to automatically download these files? [y/n]: ')
        if 'y' in prompt.lower():
            with open('autograder.py', 'w') as new:
                new.write(contents)
                print('... autograder.py updated!')
            exit(0)
        else:
            print('You can download the new autograder from the following link:')
            print()
            print('\t' + os.path.join(remote, 'autograder.py'))
            print()
            return True
    return False

def run_all_tests():
    """Runs a command line interface for the autograder."""
    parser = argparse.ArgumentParser(description='CS61A autograder')
    parser.add_argument('-u', '--unlock', type=str, 
                        help='Unlocks the specified question')
    parser.add_argument('-q', '--question', type=str,
                        help='Run tests for the specified question')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Runs all tests, regardless of failures')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Enables interactive mode upon failure')
    args = parser.parse_args()

    with open('unlocked_tests.pkl', 'rb') as f:
        unlocked_tests = pickle.load(f)
    new = check_for_updates(unlocked_tests['project_info']['remote'],
                            __version__)
    if new:
        exit(0)
    print()

    if args.unlock:
        with open('locked_tests.pkl', 'rb') as f:
            locked_tests = pickle.load(f)
        unlock(args.unlock, locked_tests, unlocked_tests)

        with open('locked_tests.pkl', 'wb') as f:
            pickle.dump(locked_tests, f, pickle.HIGHEST_PROTOCOL)
        with open('unlocked_tests.pkl', 'wb') as f:
            pickle.dump(unlocked_tests, f, pickle.HIGHEST_PROTOCOL)
    else:
        if args.question:
            tests = get_test(unlocked_tests['tests'], args.question)
            if not tests:
                print('Test {} does not exist'.format(args.question))
                exit(1)
            tests = [tests]
        else:
            tests = unlocked_tests['tests']

        global_frame = {}
        for line in unlocked_tests['project_info']['imports']:
            exec(line, global_frame)
        for test in tests:
            passed = run(test, global_frame, args.interactive)
            if not args.all and not passed:
                return
        print(underline('Note:', under='-'))
        print("""Remember that the tests in this autograder are not exhaustive, so try your own tests in the interpreter!""")


if __name__ == '__main__':
    run_all_tests()
