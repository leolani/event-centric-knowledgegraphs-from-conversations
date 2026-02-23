import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer as lemmatizer

def head_word(phrase):
    if phrase.count(" ") == 0:
        return phrase
    return phrase.split()[-1]  # simple head heuristic

def get_synset(term):
    #synsets = wn.synsets(term.replace(" ", "_"), pos=wn.NOUN)
    synsets = wn.synsets(term.replace(" ", "_"))
    if not synsets:
        lemma = lemmatizer().lemmatize(word=term.replace(" ", "_"), pos="n")
        synsets = wn.synsets(lemma)
    if not synsets:
        lemma = lemmatizer().lemmatize(word=term.replace(" ", "_"), pos="v")
        synsets = wn.synsets(lemma)
    if not synsets:
        lemma = lemmatizer().lemmatize(word=term.replace(" ", "_"), pos="a")
        synsets = wn.synsets(lemma)
    return synsets[0] if synsets else None

def lowest_common_hypernym(phrases):
    synsets = []
    for p in phrases:
        syn = get_synset(head_word(p))
        if syn:
            synsets.append(syn)

    if not synsets:
        return None

    lch = synsets[0]
    for syn in synsets[1:]:
        common = lch.lowest_common_hypernyms(syn)
        if not common:
            return None
        lch = common[0]

    return lch.lemma_names()[0] if lch else None


if __name__ == "__main__":
    nltk.download("wordnet")
    nltk.download("wordnet")
    ohrases = ["I like to eat pizza", "I like to eat pasta"]
    print(lowest_common_hypernym(ohrases))