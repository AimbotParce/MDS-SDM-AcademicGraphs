// To import data into the Neo4j docker container, you must first copy the csv
// files you want to import into the "import" folder within the Neo4j storage.
// 
// (If you are using the provided compose file, in the root project, there 
// should be a folder called "neo4j", which, when the container is created,
// will be mounted to the Neo4j storage. The "import" folder is within that
// mounted storage.)
// 
// After you have copied the csv files into the "import" folder, you can run 
// the following commands in the Neo4j browser to import the data.

// Publication Nodes
load csv with headers from 'file:///nodes-papers-1.csv' as row
merge (p:Publication {paperID:row.paperID, url:row.url, title:row.title, isOpenAccess:row.isOpenAccess})
set p.openAccessPDFUrl=row.openAccessPDFUrl, p.embedding=row.embedding, p.tldr=row.tldr, p.abstract=row.abstract, p.year=row.year, p.publicationTypes=row.publicationTypes;

// Field of Study Nodes
load csv with headers from 'file:///nodes-fieldsofstudy-1.csv' as row
merge (f:FieldOfStudy {name:row.name});

load csv with headers from 'file:///nodes-proceedings-1.csv' as row
merge (p:Proceedings {proceedingsID:row.proceedingsID, year:row.year});

load csv with headers from 'file:///nodes-journalvolumes-1.csv' as row
merge (j:JournalVolume {journalVolumeID:row.journalVolumeID, volume:row.volume});

load csv with headers from 'file:///nodes-otherpublicationvenues-1.csv' as row
merge (v:OtherPublicationVenue {venueID:row.venueID, name:row.name, alternateNames: row.alternateNames})
set v.url=row.url;

load csv with headers from 'file:///nodes-journals-1.csv' as row
merge (j:Journal {journalID: row.journalID, name: row.name, alternateNames: row.alternateNames})
set j.url=row.url;

load csv with headers from 'file:///nodes-workshops-1.csv' as row
merge (w:Workshop {workshopID: row.workshopID, name: row.name, alternateNames: row.alternateNames})
set w.url=row.url;

load csv with headers from 'file:///nodes-conferences-1.csv' as row
merge (c:Conference {conferenceID: row.conferenceID, name: row.name, alternateNames: row.alternateNames})
set c.url=row.url;

load csv with headers from 'file:///nodes-cities-1.csv' as row
merge (c:City {name: row.name});

load csv with headers from 'file:///nodes-authors-1.csv' as row
merge (a:Author {authorID: row.authorID, url: row.url, name: row.name})
set a.homepage=row.homepage, a.hIndex=row.hIndex;

load csv with headers from 'file:///nodes-organizations-1.csv' as row
merge (o:Organization {name: row.name});

// ------- Edges -------

// Citation Edges
load csv with headers from 'file:///edges-citations-1.csv' as row
match (cited:Publication {paperID:row.citedPaperID})
match (citing:Publication {paperID:row.citingPaperID})
merge (citing)-[c:Cites {isInfluential:row.isInfluential, contextsWithIntent:row.contextsWithIntent}]->(cited);