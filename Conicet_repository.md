**Semantic corpus: adding papers from Argentina**

This branch aims to add adapters and resources in order to use the available information in the 
argentinian repository that belongs to CONICET (a well-known research organization). 

You can find the official website here:
````
https://ri.conicet.gov.ar/
````
This is a quick guide, hope it helps you understand the main changes introduced!

The architecture I resorted to, goes as follows:

1) **Queries**\
First and foremost, take into account the unavailability of xml files, so every query should request for PDFs.
Create the file ```my_first_query.py``` in the root folder and add:

````
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="argentine_reports",
    query_string='("agrochemicals")', 
    output_dir=Path("temp/queries/conicet_query"),
    repository="conicet",
    limit=10,
    formats=["pdf"], 
)
````

Matter-of-factly, ```query_name```, ```query_string```, ```limit```  and ```output_dir``` depend on the interests of each user,
this is just an example!
JSON metadata is generated and the PDF files downloaded so that the HTML table can be built. 
The query is cleaned in conicet.py

2) **Search and scraping**
* The endpoint used in ```conicet.py``` is https://ri.conicet.gov.ar/discover

* Sanitizing the input query (removing inverted commas and parenthesis) is of vital importance
when trying to void failures in DSpace URL queries.

```clean_query = query.strip('()"\' ')```

Params used: 
```
{"query": clean_query, "rpp": min(limit, 20)}
```
rpp = results per page

* HTTPS requests with rate limiting
It makes use of _scraper.py which has a delay of 1.0 second between requests. 
Such behaviour prevents the server from becoming blocked. 

*  BeautifulSoup looks the ```a[href*="/handle/11336/"]``` elements up in the HTML results, aiming to identify the 
UIDs

* Once inside the website (that of the individual paper - i.e. /handle/11336/...) the <meta> tags are extracted.

*  Finally, _ids.py turns URLs or handles such as https://ri.conicet.gov.ar/handle/11336/12345
into the standard format: conicet_11336_12345.
Avoiding the use of / \ is fundamental if we want to avoid problems with the Filesystem. 
It is the best way to provide safety since Windows, Linux and macOS understand those signs as nested folders.

3) **Processing pipeline and revision**\
Tee function workflow.py:64-150 is in charge of this task. 
Results are saved into search_results.json
PDF's and metadata are downloaded
The final step: the review_table is exported with interactive formats (including the HTML view) to 
temp/queries/conicet_query/review. 

Comment: 2) and 3) happen automatically after running the query in 1)

4) Should you want to review the table, discarding or accepting each paper, run the next lines:\



5) **Tests**
Last but not least, the file test_conicet.py provides a handful of tests to analyse and control the use 
of this new tool.