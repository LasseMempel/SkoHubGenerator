import requests
import pandas as pd
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDF, DC, DCTERMS, RDFS, VANN

def csv2Df(link, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(requests.get(link).text.encode("ISO-8859-1").decode())
    df = pd.read_csv(filename, encoding="utf-8")

    # fix in table pls!
    # fix to replace linebreaks with pipeseperators for mapping properties, which don't follow the seperator rules
    for col in ["closeMatch", "relatedMatch", "exactMatch"]:
        if col in df.columns:
            df[col] = df[col].map(lambda x: "|".join(x.split("\n")) if isinstance(x, str) else x)
    
    return df


"""
def useSemanticAatUris(df):
    for index, row in df.iterrows():
        if row["prefLabel"] and isinstance(row["prefLabel"], str) and row["notation"] and isinstance(row["notation"], str):
            # in columns "closeMatch" and "relatedMatch" replace "vocab.getty.edu/page/aat/" with vocab.getty.edu/aat/
            oldRelatedMatch = row["relatedMatch"]
            oldCloseMatch = row["closeMatch"]
            if oldRelatedMatch and isinstance(oldRelatedMatch, str):
                df.at[index, "relatedMatch"] = oldRelatedMatch.replace("vocab.getty.edu/page/aat/", "vocab.getty.edu/aat/")
            if oldCloseMatch and isinstance(oldCloseMatch, str):
                df.at[index, "closeMatch"] = oldCloseMatch.replace("vocab.getty.edu/page/aat/", "vocab.getty.edu/aat/")
    return df
"""

def row2Triple(i, g, subj, pred, obj, isLang, namespace, scheme):
    i = i.strip()
    if i == "":
        print("Empty cell")
        print(subj, pred, obj)
        return g
    if obj == URIRef:
        if pred in [SKOS.broader, SKOS.narrower, SKOS.related]:
            if i != "top":
                g.add ((subj, pred, URIRef(namespace + i)))
                if pred == SKOS.broader:
                    g.add ((URIRef(namespace + i), SKOS.narrower, subj))
            else:
                g.add ((subj, SKOS.topConceptOf, scheme))
        else:
            g.add ((subj, pred, URIRef(i))) #urllib.parse.quote(i)
    else:
        if isLang:
            if len(i) > 2 and i[-3] == "@":
                i, baseLanguageLabel = i.split("@")
            g.add ((subj, pred, obj(i, lang= baseLanguageLabel)))
        else:
            g.add ((subj, pred, obj(i)))
    return g

def df2Skos(schemeDf, conceptsDf):

    g = Graph()

    # extract and declare conceptScheme and namespace
    for index, row in schemeDf.iterrows():
        if row["ConceptScheme"] and isinstance(row["ConceptScheme"], str) and row["namespace"] and isinstance(row["namespace"], str):
            scheme = URIRef(row["ConceptScheme"])
            g.add ((scheme, RDF.type, SKOS.ConceptScheme))
            namespace = row["namespace"]
            g.add((scheme, VANN.preferredNamespaceUri, Literal(namespace)))

    # declare conceptScheme metadata
    for prop, pred, obj, isLang in propertyTuples:
        if prop in schemeDf.columns:
            if not isinstance(row[prop], float):
                if seperator in row[prop]:
                    seperatedValues = row[prop].split(seperator)
                else:
                    seperatedValues = [row[prop]]
                for value in seperatedValues:
                    g = row2Triple(value, g, scheme, pred, obj, isLang, namespace, scheme)

    # declare concepts
    for index, row in conceptsDf.iterrows():
        # check if prefLabel and notation have a non empty string value
        if row["prefLabel"] and isinstance(row["prefLabel"], str) and row["notation"] and isinstance(row["notation"], str):
            #print(row["prefLabel"], row["notation"])
            concept = URIRef(namespace + row['notation'])
            g.add ((concept, RDF.type, SKOS.Concept))
            for prop, pred, obj, isLang in propertyTuples:
                if prop in df.columns:
                    if not isinstance(row[prop], float):
                        if seperator in row[prop]:
                            seperated = row[prop].split(seperator)
                            langs = [x.split("@") for x in seperated]
                            for i in range(len(seperated)):
                                g = row2Triple(seperated[i], g, concept, pred, obj, isLang, baseLanguageLabel, namespace, scheme)
                        else:
                            g = row2Triple(row[prop], g, concept, pred, obj, isLang, baseLanguageLabel, namespace, scheme)
            g.add ((concept, SKOS.inScheme, scheme))
            if row["broader"] == "top":
                g.add ((scheme, SKOS.hasTopConcept, concept))
                g.add ((concept, SKOS.topConceptOf, scheme))
    return g

def main():
    schemeDf = csv2Df(schemeLink, "schemeData.csv")
    conceptsDf = csv2Df(conceptsLink, "conceptsData.csv")
    graph = df2Skos(schemeDf, conceptsDf)
    graph.serialize(destination='scheme.ttl', format='turtle')   

conceptsLink = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJV7qC1QYCAYghp8SX09EatvnXPurJ9ZMAsGE1iUrPIxL4nLiyXlYBtKBi1Zf1xTG10AXzUp3pZcxx/pub?gid=0&single=true&output=csv"
schemeLink = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJV7qC1QYCAYghp8SX09EatvnXPurJ9ZMAsGE1iUrPIxL4nLiyXlYBtKBi1Zf1xTG10AXzUp3pZcxx/pub?gid=157607640&single=true&output=csv"
baseLanguageLabel = "de"

propertyTuples = [
    # SKOS Mapping Properties
    ("broadMatch", SKOS.broadMatch, URIRef, False),
    ("narrowMatch", SKOS.narrowMatch, URIRef, False),
    ("relatedMatch", SKOS.relatedMatch, URIRef, False),
    ("closeMatch", SKOS.closeMatch, URIRef, False),
    ("exactMatch", SKOS.exactMatch, URIRef, False),
    
    # SKOS Semantic Relations
    ("broader", SKOS.broader, URIRef, False),
    ("narrower", SKOS.narrower, URIRef, False),
    ("related", SKOS.related, URIRef, False),

    # SKOS Lexical Labels
    ("prefLabel", SKOS.prefLabel, Literal, True),
    ("altLabel", SKOS.altLabel, Literal, True),
    ("hiddenLabel", SKOS.hiddenLabel, Literal, True),   
    
    # SKOS Notations
    ("notation", SKOS.notation, Literal, False),

    # SKOS Documentation Properties
    ("note", SKOS.note, Literal, True),
    ("changeNote", SKOS.changeNote, Literal, True),
    ("definition", SKOS.definition, Literal, True),
    ("editorialNote", SKOS.editorialNote, Literal, True),
    ("example", SKOS.example, Literal, True),
    ("historyNote", SKOS.historyNote, Literal, True),
    ("scopeNote", SKOS.scopeNote, Literal, True),

    # DCTERMS Metadata Properties
    ("creator", DCTERMS.creator, Literal, False),
    ("contributor", DCTERMS.contributor, Literal, False),
    ("publisher", DCTERMS.publisher, Literal, False),
    ("rights", DCTERMS.rights, Literal, False),
    ("source", DCTERMS.source, Literal, False),
    ("subject", DCTERMS.subject, Literal, True),
    ("created", DCTERMS.created, Literal, False),
    ("license", DCTERMS.license, Literal, False),
    ("modified", DCTERMS.modified, Literal, False),
    ("title", DCTERMS.title, Literal, True),
    ("description", DCTERMS.description, Literal, True),
    
    # Other Properties
    ("seeAlso", RDFS.seeAlso, Literal, False),
]

seperator = "|"

main()