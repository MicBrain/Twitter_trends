"""Visualizing Twitter Sentiment Across America"""

from data import word_sentiments, load_tweets
from datetime import datetime
from geo import us_states, geo_distance, make_position, longitude, latitude
from maps import draw_state, draw_name, draw_dot, wait
from string import ascii_letters
from ucb import main, trace, interact, log_current_line


###################################
# Phase 1: The Feelings in Tweets #
###################################

# The tweet abstract data type, implemented as a dictionary.

def make_tweet(text, time, lat, lon):
    """Return a tweet, represented as a Python dictionary.

    text  -- A string; the text of the tweet, all in lowercase
    time  -- A datetime object; the time that the tweet was posted
    lat   -- A number; the latitude of the tweet's location
    lon   -- A number; the longitude of the tweet's location

    >>> t = make_tweet("just ate lunch", datetime(2012, 9, 24, 13), 38, 74)
    >>> tweet_text(t)
    'just ate lunch'
    >>> tweet_time(t)
    datetime.datetime(2012, 9, 24, 13, 0)
    >>> p = tweet_location(t)
    >>> latitude(p)
    38
    >>> tweet_string(t)
    '"just ate lunch" @ (38, 74)'
    """
    return {'text': text, 'time': time, 'latitude': lat, 'longitude': lon}  #returns dictionary representing the tweet, given information provided by operands

def tweet_text(tweet):
    """Return a string, the words in the text of a tweet."""
    return tweet['text'] #calls dictionaty returned by make_tweet function, and uses key to return text only (as a string)

def tweet_time(tweet):
    """Return the datetime representing when a tweet was posted."""
    return tweet['time'] #calls dictionaty returned by make_tweet function, and uses key to return time only

def tweet_location(tweet):
    """Return a position representing a tweet's location."""
    return make_position(tweet['latitude'], tweet['longitude']) #uses imported make_position function and dictionary calls to create tweet_location

# The tweet abstract data type, implemented as a function.

def make_tweet_fn(text, time, lat, lon):
    """An alternate implementation of make_tweet: a tweet is a function.

    >>> t = make_tweet_fn("just ate lunch", datetime(2012, 9, 24, 13), 38, 74)
    >>> tweet_text_fn(t)
    'just ate lunch'
    >>> tweet_time_fn(t)
    datetime.datetime(2012, 9, 24, 13, 0)
    >>> latitude(tweet_location_fn(t))
    38
    """
    # Please don't call make_tweet in your solution
    dictionary = {'text': text,'time': time,'lat': lat,'lon': lon}
    def find(key):
        return dictionary[key]   
    return find #returns function that takes operand and makes it the key called for the definied 'dictionary'

def tweet_text_fn(tweet):
    """Return a string, the words in the text of a functional tweet."""
    return tweet('text')

def tweet_time_fn(tweet):
    """Return the datetime representing when a functional tweet was posted."""
    return tweet('time')

def tweet_location_fn(tweet):
    """Return a position representing a functional tweet's location."""
    return make_position(tweet('lat'), tweet('lon'))

### === +++ ABSTRACTION BARRIER +++ === ###

def tweet_words(tweet):
    """Return the words in a tweet."""
    return extract_words(tweet_text(tweet))

def tweet_string(tweet):
    """Return a string representing a functional tweet."""
    location = tweet_location(tweet)
    point = (latitude(location), longitude(location))
    return '"{0}" @ {1}'.format(tweet_text(tweet), point)

def extract_words(text):
    """Return the words in a tweet, not including punctuation.

    >>> extract_words('anything else.....not my job')
    ['anything', 'else', 'not', 'my', 'job']
    >>> extract_words('i love my job. #winning')
    ['i', 'love', 'my', 'job', 'winning']
    >>> extract_words('make justin # 1 by tweeting #vma #justinbieber :)')
    ['make', 'justin', 'by', 'tweeting', 'vma', 'justinbieber']
    >>> extract_words("paperclips! they're so awesome, cool, & useful!")
    ['paperclips', 'they', 're', 'so', 'awesome', 'cool', 'useful']
    >>> extract_words('@(cat$.on^#$my&@keyboard***@#*')
    ['cat', 'on', 'my', 'keyboard']
    """
    words = ''
    for i in text: #goes through every character in operand 'text' and created a list with only words and spaces by adding the letter if ascii letter to the list, and a space if not
        if i in ascii_letters:
            words += i
        else:
            words += ' '
    return words.split() #returns a list containing only the words, as it splits the existing list by blank space, which leaves only the collection of letters in their respective words

def make_sentiment(value):
    """Return a sentiment, which represents a value that may not exist.
    """
    assert value is None or (value >= -1 and value <= 1), 'Illegal sentiment value'
    return value

def has_sentiment(s):
    """Return whether sentiment s has a value."""
    return s != None

def sentiment_value(s): #version of has sentiment that returns the value rather than true or false with the same intended effect
    """Return the value of a sentiment s."""
    assert has_sentiment(s), 'No sentiment value'
    return s

def get_word_sentiment(word):
    """Return a sentiment representing the degree of positive or negative
    feeling in the given word.

    >>> sentiment_value(get_word_sentiment('good'))
    0.875
    >>> sentiment_value(get_word_sentiment('bad'))
    -0.625
    >>> sentiment_value(get_word_sentiment('winning'))
    0.5
    >>> has_sentiment(get_word_sentiment('Berkeley'))
    False
    """
    # Learn more: http://docs.python.org/3/library/stdtypes.html#dict.get
    return make_sentiment(word_sentiments.get(word))

def analyze_tweet_sentiment(tweet):
    """ Return a sentiment representing the degree of positive or negative
    sentiment in the given tweet, averaging over all the words in the tweet
    that have a sentiment value.

    If no words in the tweet have a sentiment value, return
    make_sentiment(None).

    >>> t1 = trends.make_tweet("Help, I'm trapped in an autograder factory and I can't get out!".lower(), None, 0, 0)
    >>> t2 = trends.make_tweet('The thing that I love about hating things that I love is that I hate loving that I hate doing it.'.lower(), None, 0, 0)
    >>> t3 = trends.make_tweet('Peter Piper picked a peck of pickled peppers'.lower(), None, 0, 0)
    >>> round(trends.sentiment_value(analyze_tweet_sentiment(t1)), 5)
    >>> positive = make_tweet('i love my job. #winning', None, 0, 0)
    >>> round(sentiment_value(analyze_tweet_sentiment(positive)), 5)
    0.29167
    >>> negative = make_tweet("saying, 'i hate my job'", None, 0, 0)
    >>> sentiment_value(analyze_tweet_sentiment(negative))
    -0.25
    >>> no_sentiment = make_tweet("berkeley golden bears!", None, 0, 0)
    >>> has_sentiment(analyze_tweet_sentiment(no_sentiment))
    False
    """
    sent_list = list(sentiment_value(get_word_sentiment(word)) for word in tweet_words(tweet) if has_sentiment(get_word_sentiment(word))) #creates a list of the sentiments for each word in the tweet that has a sentiment all of the words
    if not sent_list: #if the list is empty (no word in the tweet had sentiments) then return a sentiment of None
        return make_sentiment(None)
 
    total = sum(sent_list)
    length = len(sent_list)
    return make_sentiment(total / length) #returns sentiment for entire tweet by averaging the values in the list (or the sentiments of the words in the tweet that had sentiments)


#################################
# Phase 2: The Geometry of Maps #
#################################

def find_centroid(polygon):
    """Find the centroid of a polygon.


  from functools import reduce
    sent_list = list((get_word_sentiment(word)) for word in extract_words(tweet_text(tweet)) if has_sentiment(word))
    total = reduce(lambda x,y: x+y, sent_list)
    return total/len(sent_list)

    http://en.wikipedia.org/wiki/Centroid#Centroid_of_polygon

    polygon -- A list of positions, in which the first and last are the same

    Returns: 3 numbers; centroid latitude, centroid longitude, and polygon area

    Hint: If a polygon has 0 area, use the latitude and longitude of its first
    position as its centroid.

    >>> p1, p2, p3 = make_position(1, 2), make_position(3, 4), make_position(5, 0)
    >>> triangle = [p1, p2, p3, p1]  # First vertex is also the last vertex
    >>> round5 = lambda x: round(x, 5) # Rounds floats to 5 digits
    >>> tuple(map(round5, find_centroid(triangle)))
    (3.0, 2.0, 6.0)
    >>> tuple(map(round5, find_centroid([p1, p3, p2, p1])))
    (3.0, 2.0, 6.0)
    >>> tuple(map(float, find_centroid([p1, p2, p1])))  # A zero-area polygon
    (1.0, 2.0, 0.0)
    """
    initial = 0  #The initial value of the area and the coordinates of the centroid
    X=0
    Y=0
    for i in range(0, len(polygon) - 1):
        initial = initial + (latitude(polygon[i]) * longitude(polygon[i+1]) - latitude(polygon[i+1]) * longitude(polygon[i])) #Uses the equation that produces the area of the polygon
    area = initial / 2
    if area == 0:
        return (latitude(polygon[0]), longitude(polygon[0]), 0)
    else:
        for i in range(0, len(polygon)-1):
            X = X + (latitude(polygon[i]) + latitude(polygon[i+1])) * (latitude(polygon[i]) * longitude(polygon[i+1]) - latitude(polygon[i+1]) * longitude(polygon[i]))  #The equation for the X-coordinate of the centroid
            Y = Y + (longitude(polygon[i]) + longitude(polygon[i+1])) * (latitude(polygon[i]) * longitude(polygon[i+1]) - latitude(polygon[i+1]) * longitude(polygon[i]))  #The equation for the Y-coordinate of the centroid
        X = X / (6 * area)
        Y = Y / (6 * area)
    return X, Y, abs(area)  #The final values of the coordinates of the the centroid and the area of the polygon


def find_state_center(polygons):
    """Compute the geographic center of a state, averaged over its polygons.

    The center is the average position of centroids of the polygons in polygons,
    weighted by the area of those polygons.

    Arguments:
    polygons -- a list of polygons

    >>> ca = find_state_center(us_states['CA'])  # California
    >>> round(latitude(ca), 5)
    37.25389
    >>> round(longitude(ca), 5)
    -119.61439

    >>> hi = find_state_center(us_states['HI'])  # Hawaii
    >>> round(latitude(hi), 5)
    20.1489
    >>> round(longitude(hi), 5)
    -156.21763
    """
    #The initial values of the area of all polygons and the average position of centroid of polygons
    Area_overall = 0
    X_overall = 0
    Y_overall = 0

    for i in range(0, len(polygons)):
        Area_overall = Area_overall + find_centroid(polygons[i])[2]  #The formala for calculating the are of all polygons combined
        X_overall = X_overall + find_centroid(polygons[i])[0] * find_centroid(polygons[i])[2]  #The X-axis of average position of centroid of polygons
        Y_overall = Y_overall + find_centroid(polygons[i])[1] * find_centroid(polygons[i])[2]  #The Y-axis of average position of centroid of polygons
    X_overall, Y_overall = X_overall / Area_overall, Y_overall/Area_overall
    return make_position(X_overall, Y_overall)  #The final values of the X and Y coordinates.

###################################
# Phase 3: The Mood of the Nation #
###################################

def group_tweets_by_state(tweets):
    """Return a dictionary that aggregates tweets by their nearest state center.

    The keys of the returned dictionary are state names, and the values are
    lists of tweets that appear closer to that state center than any other.

    tweets -- a sequence of tweet abstract data types

    >>> sf = make_tweet("welcome to san francisco", None, 38, -122)
    >>> ny = make_tweet("welcome to new york", None, 41, -74)
    >>> two_tweets_by_state = group_tweets_by_state([sf, ny])
    >>> len(two_tweets_by_state)
    2
    >>> california_tweets = two_tweets_by_state['CA']
    >>> len(california_tweets)
    1
    >>> tweet_string(california_tweets[0])
    '"welcome to san francisco" @ (38, -122)'
    """
    tweets_by_state = {}
    states_centers = {state: find_state_center(us_states[state]) for state in us_states.keys()} # creates the dictionary state_centers that contains each state it's its respective state center   
    for tweet in tweets: # goes through every tweet and assigns it to the dictionary tweets_by_state by its closest state center
      closest, state_name = 0, '' 
      for state in states_centers:
        distance = geo_distance(tweet_location(tweet), states_centers[state]) # adds the distance from tweet to each state center to the list called distances 
        if closest == 0 or distance < closest:
          closest = distance  # if current state is closer than previous closest state, reassigns closest and state_name accordingly
          state_name = state
      if state_name in tweets_by_state:   # if this state is already defined in the dictionary then the tweets is added to the existing state key
        tweets_by_state[state_name].append(tweet) 
      else: # if this state does not already contain a position in the directoy, then one is created
        tweets_by_state[state_name] = [tweet]
    return tweets_by_state   # Returns the dictionary that has aggregated tweets by their nearest state center

def average_sentiments(tweets_by_state):
    """Calculate the average sentiment of the states by averaging over all
    the tweets from each state. Return the result as a dictionary from state
    names to average sentiment values (numbers).

    If a state has no tweets with sentiment values, leave it out of the
    dictionary entirely.doc  Do NOT include states with no tweets, or with tweets
    that have no sentiment, as 0.  0 represents neutral sentiment, not unknown
    sentiment.

    tweets_by_state -- A dictionary from state names to lists of tweets
    """
    averaged_state_sentiments = {}
    for key in tweets_by_state.keys():
        tweets_per_state = tweets_by_state[key] #makes tweets_per_state a list of tweets per that state, and does this (and the code below) for each state
        total_tweets = 0 #counter for number of tweets that have a sentiment
        for x in range(len(tweets_per_state)): 
            if has_sentiment(analyze_tweet_sentiment(tweets_per_state[x])) == False: #if tweet doesnt have a sentiment replace it will a sentiment value of 0
                tweets_per_state[x] = 0
            else:
                total_tweets += 1 
                tweets_per_state[x] = sentiment_value(analyze_tweet_sentiment(tweets_per_state[x])) #if this tweet has a sentiment, replace it with the sentiment value
        if total_tweets != 0: #if no tweets in this state have senitments then skip this step, go to next state
            averaged_state_sentiments[key] = sum(tweets_per_state) / (total_tweets) #returns average sentiment of all tweets per this state that have sentiments
    return averaged_state_sentiments

##########################
# Command Line Interface #
##########################

def print_sentiment(text='Are you virtuous or verminous?'):
    """Print the words in text, annotated by their sentiment scores."""
    words = extract_words(text.lower())
    layout = '{0:>' + str(len(max(words, key=len))) + '}: {1:+}'
    for word in words:
        s = get_word_sentiment(word)
        if has_sentiment(s):
            print(layout.format(word, sentiment_value(s)))

def draw_centered_map(center_state='TX', n=10):
    """Draw the n states closest to center_state."""
    us_centers = {n: find_state_center(s) for n, s in us_states.items()}
    center = us_centers[center_state.upper()]
    dist_from_center = lambda name: geo_distance(center, us_centers[name])
    for name in sorted(us_states.keys(), key=dist_from_center)[:int(n)]:
        draw_state(us_states[name])
        draw_name(name, us_centers[name])
    draw_dot(center, 1, 10)  # Mark the center state with a red dot
    wait()

def draw_state_sentiments(state_sentiments):
    """Draw all U.S. states in colors corresponding to their sentiment value.

    Unknown state names are ignored; states without values are colored grey.

    state_sentiments -- A dictionary from state strings to sentiment values
    """
    for name, shapes in us_states.items():
        sentiment = state_sentiments.get(name, None)
        draw_state(shapes, sentiment)
    for name, shapes in us_states.items():
        center = find_state_center(shapes)
        if center is not None:
            draw_name(name, center)

def draw_map_for_query(term='my job', file_name='tweets2011.txt'):
    """Draw the sentiment map corresponding to the tweets that contain term.

    Some term suggestions:
    New York, Texas, sandwich, my life, justinbieber
    """
    tweets = load_tweets(make_tweet, term, file_name)
    tweets_by_state = group_tweets_by_state(tweets)
    state_sentiments = average_sentiments(tweets_by_state)
    draw_state_sentiments(state_sentiments)
    for tweet in tweets:
        s = analyze_tweet_sentiment(tweet)
        if has_sentiment(s):
            draw_dot(tweet_location(tweet), sentiment_value(s))
    wait()

def swap_tweet_representation(other=[make_tweet_fn, tweet_text_fn,
                                     tweet_time_fn, tweet_location_fn]):
    """Swap to another representation of tweets. Call again to swap back."""
    global make_tweet, tweet_text, tweet_time, tweet_location
    swap_to = tuple(other)
    other[:] = [make_tweet, tweet_text, tweet_time, tweet_location]
    make_tweet, tweet_text, tweet_time, tweet_location = swap_to


@main
def run(*args):
    """Read command-line arguments and calls corresponding functions."""
    import argparse
    parser = argparse.ArgumentParser(description="Run Trends")
    parser.add_argument('--print_sentiment', '-p', action='store_true')
    parser.add_argument('--draw_centered_map', '-d', action='store_true')
    parser.add_argument('--draw_map_for_query', '-m', type=str)
    parser.add_argument('--tweets_file', '-t', type=str, default='tweets2011.txt')
    parser.add_argument('--use_functional_tweets', '-f', action='store_true')
    parser.add_argument('text', metavar='T', type=str, nargs='*',
                        help='Text to process')
    args = parser.parse_args()
    if args.use_functional_tweets:
        swap_tweet_representation()
        print("Now using a functional representation of tweets!")
        args.use_functional_tweets = False
    if args.draw_map_for_query:
        draw_map_for_query(args.draw_map_for_query, args.tweets_file)
        print(args.tweets_file)
        return
    for name, execute in args.__dict__.items():
        if name != 'text' and name != 'tweets_file' and execute:
            globals()[name](' '.join(args.text))
