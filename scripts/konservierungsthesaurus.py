import requests
import pandas as pd
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDF, DCTERMS, RDFS, VANN
from io import StringIO

def csv2Df(link, filename):

    response = requests.get(link).text
    df = pd.read_csv(StringIO(response), sep="\t")
    df.to_csv(filename, index=False)
    
    return df

def row2Triple(value, g, subj, pred, obj, isLang, namespace, scheme, lang):

    value = value.strip()
    if value == "":
        print("Empty cell")
        print(subj, pred, obj)
        return g
    if obj == URIRef:
        if pred in [SKOS.broader, SKOS.narrower, SKOS.related]:
            if value != "top":
                g.add ((subj, pred, URIRef(namespace + value)))
                if pred == SKOS.broader:
                    g.add ((URIRef(namespace + value), SKOS.narrower, subj))
            else:
                g.add ((subj, SKOS.topConceptOf, scheme))
        else:
            g.add ((subj, pred, URIRef(value)))
    else:
        if isLang:
            g.add ((subj, pred, obj(value, lang= lang)))
        else:
            g.add ((subj, pred, obj(value)))
    return g

def propertyWalk(df, row, g, subj, scheme, namespace):

    #for prop, pred, obj, isLang in propertyDict:
    for col in df.columns:
        if "@" in col:
            colProp, lang = col.split("@")
        else:
            colProp, lang = col, baseLanguageLabel
        
        if colProp in propertyDict:
            pred, obj, isLang = propertyDict[colProp]
            if not isinstance(row[col], float):
                if seperator in row[col]:
                    seperatedValues = row[col].split(seperator)
                else:
                    seperatedValues = [row[col]]
                for value in seperatedValues:
                    g = row2Triple(value, g, subj, pred, obj, isLang, namespace, scheme, lang)
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
            g = propertyWalk(schemeDf, row, g, scheme, scheme, namespace)

    # declare concepts
    for index, row in conceptsDf.iterrows():
        # check if prefLabel and notation have a non empty string value
        if row["prefLabel"+"@" + baseLanguageLabel] and isinstance(row["prefLabel"+"@" + baseLanguageLabel], str) and row["notation"] and isinstance(row["notation"], str):
            concept = URIRef(namespace + row['notation'])
            g.add ((concept, RDF.type, SKOS.Concept))
            g.add ((concept, SKOS.inScheme, scheme))
            g = propertyWalk(conceptsDf, row, g, concept, scheme, namespace)
            if row["broader"] == "top":
                g.add ((scheme, SKOS.hasTopConcept, concept))
                g.add ((concept, SKOS.topConceptOf, scheme))
    return g

def main():
    schemeDf = csv2Df(schemeLink, "schemeData.csv")
    conceptsDf = csv2Df(conceptsLink, "conceptsData.csv")
    graph = df2Skos(schemeDf, conceptsDf)
    graph.serialize(destination='scheme.ttl', format='turtle')   

conceptsLink = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJV7qC1QYCAYghp8SX09EatvnXPurJ9ZMAsGE1iUrPIxL4nLiyXlYBtKBi1Zf1xTG10AXzUp3pZcxx/pub?gid=0&single=true&output=tsv"
schemeLink = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSJV7qC1QYCAYghp8SX09EatvnXPurJ9ZMAsGE1iUrPIxL4nLiyXlYBtKBi1Zf1xTG10AXzUp3pZcxx/pub?gid=157607640&single=true&output=tsv"
baseLanguageLabel = "de"

propertyDict = {
    # SKOS Mapping Properties
    "broadMatch": (SKOS.broadMatch, URIRef, False),
    "narrowMatch": (SKOS.narrowMatch, URIRef, False),
    "relatedMatch": (SKOS.relatedMatch, URIRef, False),
    "closeMatch": (SKOS.closeMatch, URIRef, False),
    "exactMatch": (SKOS.exactMatch, URIRef, False),
    
    # SKOS Semantic Relations
    "broader": (SKOS.broader, URIRef, False),
    "narrower": (SKOS.narrower, URIRef, False),
    "related": (SKOS.related, URIRef, False),

    # SKOS Lexical Labels
    "prefLabel": (SKOS.prefLabel, Literal, True),
    "altLabel": (SKOS.altLabel, Literal, True),
    "hiddenLabel": (SKOS.hiddenLabel, Literal, True),   
    
    # SKOS Notations
    "notation": (SKOS.notation, Literal, False),

    # SKOS Documentation Properties
    "note": (SKOS.note, Literal, True),
    "changeNote": (SKOS.changeNote, Literal, True),
    "definition": (SKOS.definition, Literal, True),
    "editorialNote": (SKOS.editorialNote, Literal, True),
    "example": (SKOS.example, Literal, True),
    "historyNote": (SKOS.historyNote, Literal, True),
    "scopeNote": (SKOS.scopeNote, Literal, True),

    # DCTERMS Metadata Properties
    "creator": (DCTERMS.creator, Literal, False),
    "contributor": (DCTERMS.contributor, Literal, False),
    "publisher": (DCTERMS.publisher, Literal, False),
    "rights": (DCTERMS.rights, Literal, False),
    "source": (DCTERMS.source, Literal, False),
    "subject": (DCTERMS.subject, Literal, True),
    "created": (DCTERMS.created, Literal, False),
    "license": (DCTERMS.license, Literal, False),
    "modified": (DCTERMS.modified, Literal, False),
    "title": (DCTERMS.title, Literal, True),
    "description": (DCTERMS.description, Literal, True),
    
    # Other Properties
    "seeAlso": (RDFS.seeAlso, Literal, False),
}

seperator = "|"

main()