**27/07**


I outlined my research topic on agrochemicals (e.g. gliphosate) and their impact. I came up with the idea of dividing the topic in three areas: 
	1) impact on health
	2) impact on natural resources 
	3) Realted  laws and regulations.  

I have already downloaded some papers which I should check, still the search goes on! 

Regarding the encyclopedia repo, it is already cloned in my pc but the env and requisites are left to be set. 

**28/07**


Since my last post I got familiarised eith the semantic_corpus tool. I set up the venv in my local IDE
Being able to understand the CLI commands was a major advance. 

Nevertheless some issues appeared when trying to download the papers. If I looked for all (sorts of file) or pdf in the 
europe_pmc repo, it would print "download" without really adding any content to the tool_research folder.

Narrowing the scope to xml, the problem has been sorted. 

I look forward to joining the FSCI meeting on Thursday

**30/07**


Attending the FSCI meeting was wonderful!
Apart from that, I added the file agrochemical_clasification.md
I deem it important to understand the wide variety of chemicals available before fully analizing their effects

I'll keep on with the research of papers and trying new tools. 

No problems today

**31/07**


New papers were found on the following topics: the impact of agrochemicals on the nitrogen and phosphorus 
cycle, secondary successions, insects and microorganisms. 

I look forward to trying the **structure** repo as well as get it working in my end device

**02/08**

I got the structure repo running in my computer. I had to enable the Developer Mode (Windows 11) i order to use the symlinks - I wasn't
aware of that.

I found some issues with the following paths: 

python -m structure.convert.docling.cli pilot/examples/iari_2024.pdf --document-id iari-2024
python -m structure.validate.html.cli pilot/examples/html/iari_2024.html

The ones actually working are:

python -m structure.convert.docling.cli pilot/examples/iari-2024/annual_report.pdf --document-id iari-2024
python -m structure.validate.html.cli pilot/examples/iari-2024/annual_report.raw.html

I tried pushing it on a branch of my own but get a 403 error. 

In order to continue with the research on agrochemical's impact, I thought of including some other aspects. 

**03/08**

I was able to run the encyclopedia repo. I faced some difficulties downloading its dependencies, yet they're solved. 
The localhost is currently loading. Loading some html file is left to be done (I had none, all the reserach on agrochemicals is stored in PDFs)

**05/08**
Up to now I have 25 files with information. I'm not sure what to do next.

**06/08**
The **Green Revolution** is the point in History where the massive use of **agrochemicals** in agriculture starts. 
Even though it looked forward to **reducing famines** in the Global South, sixty years later, hunger does not subside - at least not as fast as it shoudl have.
We have more food, indeed. Nevertherless, most of it is rotten and generating gas emissions into the environment. 
At the same time, we also suffer all the disadvantages that stem from new agressive technics. Something went terribly wrong...
In this commit I'm pushing some papers, books and reports exploring this wide background. 'Cause knowing the past, helps us understand the present ;)

~36 files

**07/08**
I was able to fully understand the query system. I ran many queries, saving the results of each in different folders.
All of them related to agrochemicals, the topic I'm doing research on. 
I've started assessing the review tables of the first two. There are many left to be checked!

Some useful information for my 'future-self':
 - In order to start the server: .\venv\Scripts\python.exe scripts/review_viewer.py serve --review-table temp/queries/agrochemicals_argentina/review/review_table.json --query-dir temp/queries/agrochemicals_argentina 
 - In order to generate the review_table.html: .\venv\Scripts\python.exe scripts/build_review_table.py --query-dir temp/queries/agrochemicals_argentina

**08/08**
Only 3 queries left to filter

**09/08**
All tables reviewd. I either included or excluded each paper. 
I should ask for guidance in order to fulfill the following steps

**14/08**
Scraping also applies to https://ri.conicet.gov.ar/discover now. It gives us a cleared approach to problems faced by the South American population

**17/08**
Documentation explaining how the CONICET repo was added to the bot is ready!

**30/08**
Glad to announce that semantic_corpus is now working with UBA repositories! At first I tried using www.repositoriouba.sisbi.uba.ar/gsdl/cgi-bin/library.cgi
BUT ('cause there's always one...) it needed captcha verification. Therefore I am using more specific repos that belong to UBA as well. 
I chose the one on agronomy and the one on Exact Sciences. The content of others is not that relevant to us. 

Most files were published as PDfs here. The JSON file is automatically generated and the HTML available witht the table.