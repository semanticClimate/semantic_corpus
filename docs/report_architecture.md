## Introduction

This report sets out to analyze the compelling need to make the developed tools accessible to everybody - even those with no expertise in the IT area. As pointed out in the last meeting, in order to reach a wider audience and thus spread climate knowledge more effectively, we are bound to provide an easy, approachable UI/UX to replace the current CLI-based usage. 

## Server

The very first step in order to achieve such goal would be hosting the #semanticClimate tools in a server with 24/7 availability. Some options worth considering: 

AWS for Nonprofits: First, the organization's nonprofit status should be verified and the free plan requested. Having done that, an EC2 would work. This is a server where the repository can be loaded and run. Configuring a CI/CD workflow would be enough to run the code automatically as soon as the server turns on or to pull changes from a Github Repository when pushed. If an Elastic IP was requested (so that the public IP is not constantly changing), it would be possible to generate our own URL by using DuckDNS. Should it be important to have staging and production environments, two virtual machines would be needed. For the time being and taking into consideration the lack of resources, I would not deem it mandatory. Choosing the appropriate EC2 for the code is also important (it depends on how much storage it needs, the smaller, the cheaper).
An SSL certificate can be configured anyway so that the website runs over HTTPS.
It is highly recommended to load the repository inside a Docker container. This makes deployments simpler and cleaner and the environment becomes independent of local variables and configurations. Naturally, it brings some disadvantages such as added complexity, port management, or writing a Dockerfile. Still, the pros outweigh the cons. 

Render: Render currently offers the most realistic free option for continuously running a small backend service. Its free tier includes web services, static sites, and managed PostgreSQL, with no credit card required. The main trade-off is that free services spin down after 15 minutes of inactivity, and the first request afterward takes 30–60 seconds to wake up (cold start). For a tool that isn't queried constantly, this delay may be acceptable; for one requiring instant response at all times, it would not be. The main disadvantage is that it only allows one member what might hinder the development. https://render.com/pricing (check the Hobby plan).

Railway: Railway's free tier is only suitable for minimal workloads. It provides a one-time credit (not renewed monthly) that is quickly used up by any continuously running service, with resources capped at 1 vCPU, 0.5 GB RAM, and 0.5 GB of persistent storage. Once the credit runs out, the app is suspended and paid usage begins. Although it supports GitHub-based and containerized deployments, its free allowance is appropriate only for short-lived tests or prototypes, not for services requiring sustained availability.

Fly.io: Fly.io no longer offers a genuine free tier. New accounts only get a short trial (around 2 VM-hours or 7 days, whichever comes first), after which a credit card is required and all usage is billed. Some accounts created before the policy changed in late 2023/early 2024 retain legacy free allowances, but these aren't available to new signups. As a result, Fly.io should now be treated as a low-cost, pay-as-you-go option rather than a free one.

Heroku: Heroku no longer has a free tier either. Salesforce discontinued free dynos, free Postgres, and free Redis on November 28, 2022, citing abuse of the free plans. The cheapest option today is the Eco dyno plan, starting at $5/month for 1,000 shared compute hours, with apps sleeping after 30 minutes of inactivity. Heroku should therefore be removed from the list of free hosting candidates.

GitHub Pages and Firebase face the same constraint in their free plans: they're designed for static websites and cannot run backend code.
Given this, Render and AWS for Nonprofits stand out as the most realistic options: Render for a quick, no-cost setup that tolerates occasional cold starts, and AWS for a more robust, always-on setup once nonprofit status is confirmed.

## Github Actions and Hooks

Taking advantage of Github’s free resources, it would be advantageous to set up actions that run the generated tests, a formatter (style, how the code looks) and a linter (prevents bad practices which may eventually lead to bugs) in order to ensure the code's reliability and enhance its quality. 

Even a previous step can be added, making it mandatory to run these checks on each endpoint device before pushing it to the repository. 

## Conclusion

In view of all the above-mentioned, we can conclude that, even though it can be a long process (it has to be applied to each repository belonging to the organization) in the end it is undoubtedly going to pay off. Only when it seeks to reach a broader audience, regardless of their IT background or the devices they use, will #semanticClimate fully accomplish its aim. 

