'''
.. py:module:: markov
    :platform: Unix

First Week's homework.
Student name:  Jared Bagley
Student Username: JBagley
Student ID: 014737165
'''
import re
import operator
import nltk
import string
import random

import os

def getAlice():
    # Download Alice's Adventures in Wonderland if it is not yet present
    alice_file = 'alice.txt'
    alice_raw = None

    if not os.path.isfile(alice_file):
        from urllib import request
        url = 'http://www.gutenberg.org/cache/epub/19033/pg19033.txt'
        response = request.urlopen(url)
        alice_raw = response.read().decode('utf8')
        with open(alice_file, 'w', encoding='utf8') as f:
            f.write(alice_raw)
    else:
        with open(alice_file, 'r', encoding='utf8') as f:
            alice_raw = f.read()

    # Remove the start and end bloat from Project Gutenberg (this is not exact, but
    # easy).
    pattern = 'I--DOWN THE RABBIT-HOLE'
    end = "End of the Project Gutenberg"
    start_match = re.search(pattern, alice_raw)
    if start_match:
        start_index = start_match.span()[1] + 1
    else:
        start_index = 0
    end_index = alice_raw.rfind(end)
    alice = alice_raw[start_index:end_index]

    # And replace more than one subsequent whitespace chars with one space
    alice = re.sub(r'\s+', ' ', alice)
    return alice;

def sanitize(token_list):
    '''
    Sanitizes a token list by only accepting valid words,
    and removes any words with non-printable characters. This will
    allow any alphanumeric character and the underscore, which should be 
    sufficient, but also filtering out characters which are considered
    un-printable by a string.
    '''
    
    # Using regular expression of a valid word
    is_word = re.compile('\w')

    # Filter out wordless punctuation
    new_list = [token for token in token_list if not any(value in ''.join(token) for value in (r'\'\'', r'\`\`', '``', '--'))]
    
    # Only select valid words, and end in a period
    new_list = [token for token in new_list if is_word.search(token)] + ['.']

    # Filter out any words with non-printable characters
    for token in new_list:
        token = ''.join(filter(lambda c: c in string.printable, token))
    return new_list;
    
def likelihood(text, state_transition_probabilities):
    '''
    Calculates the probability of text occurring given the responsible
    state transition probability model.  It does this by assuming the initial
    word has a 100% probability, and then tallies the full text probability by
    multiplying the intial probability by the probability of the next word,
    continuing until every consecutive probability is incorporated.  This results in
    the combinatorial probability of the full text.
    '''

    #Assume initial probability of 0%
    probability = 0
    #Add spaces between periods/commas so the preceding word isn't treated differently.
    token_list = text.replace(".", " .").replace(",", " ,").split()
    #Sanitize the token list
    token_list = sanitize(token_list)
    
    #Determine order of state transitions being used
    order = determineOrder(state_transition_probabilities)
    
    #Enumerate through the words, and find the probability of the word that follows
    for i, val in enumerate(token_list):
        prev_token = ''
        if i > order and i < len(token_list):
            for j in range(order, 0, -1):
                prev_token += token_list[i-1-j] + ' '
            prev_token = prev_token.strip()
            if (prev_token in state_transition_probabilities):
                #Set an initial probability if necessary
                probability = 1 if probability == 0 else probability
                #Determine next word
                next_token = token_list[i-1]
                #Determine next word's probability from this word
                if (next_token in state_transition_probabilities[prev_token]):
                    next_word_prob = state_transition_probabilities[prev_token][next_token]
                    #Multiply probability by next word's probability
                    probability *= next_word_prob

    return probability;
    
def determineOrder(state_transition_probabilities):
    # Calculate the order used by the state transition probabilities list
    maxOrder = [token.count(' ') for token in state_transition_probabilities.keys() if token.count(' ') > 0]

    # If the list is empty (no spaces), order 1, otherwise it's 1+# of spaces
    if not maxOrder:
        order = 1
    else:
        order = max(maxOrder) + 1
    
    return order;   
    
def generate(state_transition_probabilities, length=10, start=None):
    '''
    Given a model of state transition probabilities, construct a new artifact
    of supplied length, starting from the initial word given, if any.
    '''
    order = determineOrder(state_transition_probabilities)
    # Calculate the order used by the state transition probabilities list
    maxOrder = [token.count(' ') for token in state_transition_probabilities.keys() if token.count(' ') > 0]

    # If the list is empty (no spaces), order 1, otherwise it's 1+# of spaces
    if not maxOrder:
        order = 1
    else:
        order = max(maxOrder) + 1

    if start == None:
        is_word = re.compile('\w')
        #No word chosen as start, so we determine a starting point ourself from valid choices
        possible_start = [token for token in state_transition_probabilities.keys() if is_word.search(token)]
        start = random.choice(possible_start)
    elif  start.count(' ') < (order-1):
        start = random.choice([token for token in state_transition_probabilities.keys() if token.startswith(start)])
        if start == None:
            raise ValueError("Provided Start value for generate method is not in available state transitions.")
    elif not start in state_transition_probabilities.keys():
        raise ValueError("Provided Start value for generate method is not in available state transitions.")
    
    #Record our chosen word(s)
    prev = start
    new_text = []
    new_text.append(prev)
    
    # Transform the data to a cumulative distribution function (cdf)
    cdfs = {}
    for pred, succ_probs in state_transition_probabilities.items():
        items = succ_probs.items()
        # Sort the list by the second index in each item and reverse it from
        # highest to lowest.
        sorted_items = sorted(items, key=operator.itemgetter(1), reverse=True)
        cdf = []
        cumulative_sum = 0.0
        for c, prob in sorted_items:
            cumulative_sum += prob
            cdf.append([c, cumulative_sum])
        cdf[-1][1] = 1.0 # We fix the last because of the possible rounding errors.
        cdfs[pred] = cdf
    
    #Now add words so long as we haven't reached a dead end, and the length is less than the requested
    while len(new_text) < length and prev in state_transition_probabilities and len(state_transition_probabilities[prev]) > 0:
        rnd = random.random() # Random number from 0 to 1
        cdf = cdfs[prev]
        cp = cdf[0][1]
        i = 0
        # Go through the cdf until the cumulative probability is higher than the
        # random number 'rnd'.
        while rnd > cp:
            i += 1
            cp = cdf[i][1]
        succ = cdf[i][0]
        new_text.append(succ)
        prev = ' '.join(nltk.word_tokenize(' '.join(new_text))[-order:])

    #Before returning the result, we add spaces between each word, but remove them between punctuation
    return ' '.join(map(str, new_text))
    
def format_for_printing(raw_text):
    '''
    Takes raw text that has resulted from a markov chain and removes spaces
    between punctuation tokens, capitalizes the first word to make the, adds
    a period at the end to make the sentence more readable
    '''
    formatted_string = raw_text
    formatted_string=formatted_string.replace(" .", ".")
    formatted_string=formatted_string.replace(" ,", ",")
    formatted_string=replace_maintaining_case(formatted_string," n't", "n't")
    formatted_string=replace_maintaining_case(formatted_string," 's", "'s")
    formatted_string=replace_maintaining_case(formatted_string," 'll", "'ll")
    formatted_string=replace_maintaining_case(formatted_string," 've", "'ve")
    formatted_string=replace_maintaining_case(formatted_string," 're", "'re")
    formatted_string=replace_maintaining_case(formatted_string," 'd", "'d")
    formatted_string=replace_maintaining_case(formatted_string," 'm", "'m")
    
    # Remove any trailing whitespace
    formatted_string = formatted_string.strip()
    
    # Add a period, if necessary
    if not formatted_string[-1:] == ".":
        formatted_string = formatted_string + "."
    
    # Capitalize the first letter without changing case of other letters
    if formatted_string[0] in ("_", "'"):
        formatted_string =  formatted_string[1].upper() + formatted_string[1:]
    else:
        formatted_string =  formatted_string[0].upper() + formatted_string[1:]
    
    return formatted_string
    
def replace_maintaining_case(raw_text, find_text, replace_text):
    '''
    Takes raw text, and something to be replaced, but maintains the original_text
    case of the letters being replaced
    '''
    return re.sub(find_text,
             lambda m: replacement_func(m, replace_text),
             raw_text, flags=re.I)
             
def replacement_func(match, repl_pattern):
    '''
    Function for replacing text, found on StackOverflow:
    http://stackoverflow.com/questions/9208786/best-way-to-do-a-case-insensitive-replace-but-match-the-case-of-the-word-to-be-r
    '''
    match_str = match.group(0)
    repl = ''.join([r_char if m_char.islower() else r_char.upper()
                   for r_char, m_char in zip(repl_pattern, match_str)])
    repl += repl_pattern[len(match_str):]
    return repl

def markov_chain(raw_text, should_sanitize=True, order=1):
    '''
    Derive a model of state transition probabilities from supplied raw 
    text, after sanitizing the text, unless specified not to.
    '''
    # Replace more than one subsequent whitespace chars with one space
    raw_text = re.sub(r'\s+', ' ', raw_text)
    raw_text = re.sub(r'\t+', ' ', raw_text)

    # Tokenize the text into sentences.
    sentences = nltk.sent_tokenize(raw_text)

    # Tokenize each sentence to words. Each item in 'words' is a list with
    # tokenized words from that list.
    tokenized_sentences = []
    for s in sentences:
        w = nltk.word_tokenize(s)
        tokenized_sentences.append(w)

    # Sanitize the tokens of each sentence
    if should_sanitize:
        tokenized_sentences = [sanitize(sentence) for sentence in tokenized_sentences]

    # Now we are ready to create the state transitions. However, this time we
    # count the state transitions from each sentence at a time.
    transitions = {}
    for data in enumerate(tokenized_sentences):
        for i in range(len(data[1])-order):
            pred = data[1][i]
            for j in range(1, order):
                pred += " " + data[1][i+j]
            succ = data[1][i+order]
            if pred not in transitions:
                # Predecessor key is not yet in the outer dictionary, so we create
                # a new dictionary for it.
                transitions[pred] = {}
            if succ not in transitions[pred]:
                # Successor key is not yet in the inner dictionary, so we start
                # counting from one.
                transitions[pred][succ] = 1.0
            else:
                # Otherwise we just add one to the existing value.
                transitions[pred][succ] += 1.0
    
    # Compute total number of successors for each state
    totals = {}
    for pred, succ_counts in transitions.items():
        totals[pred] = sum(succ_counts.values())
        #print(pred,totals[pred])
    
    # Compute the probability for each successor given the predecessor.
    probs = {}
    for pred, succ_counts in transitions.items():
        probs[pred] = {}
        for succ, count in succ_counts.items():
            probs[pred][succ] = count / totals[pred]

    return probs, transitions

#This is test calls to each method, using the below test text for model building
#original_text = "This is a test, this is only a test.  Do not pay attention to the words in this test.  If this were not a test then something would happen."
#The resulting model is stored from analysis
#result = markov_chain(original_text, True, 1)
#result = markov_chain(getAlice(), True, 6)
#We generate new text using the model
#new = generate(result,20)
#Print out the generated text
#print(new)
#And then print the probability of that text having occurred
#print(new)
#print(likelihood(new, result))