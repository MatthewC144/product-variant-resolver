# Fandom source permission guide

Date:2026-09-16. This is a beginner-facing technical guide,not legal advice. No email or form has been sent.

## Why permission is required

Fandom's [Terms of Use](https://www.fandom.com/terms-of-use),listed as last revised2025-12-19 in the
public search result,prohibit automated access/scraping without express prior written permission. Fandom's
[Licensing page](https://www.fandom.com/licensing) separately says wiki text is generally CC BY-SA3.0,
subject to each community's actual license and attribution/share-alike requirements. The license may allow
reuse of text,but it does not cancel the platform's automated-access rule.

The project therefore cannot start a crawler or call the Fandom API merely because pages are public. General
[MediaWiki API etiquette](https://www.mediawiki.org/wiki/API:Etiquette) explains how permitted clients should
behave—serial requests,informative User-Agent,caching and`maxlag`—but does not grant Fandom permission.

## Permission request draft

Send this yourself through a current official Fandom support/contact channel. Replace bracketed values;
do not commit personal email addresses or an unredacted reply to Git.

> Subject: Request for written permission for limited read-only Hot Wheels Wiki API access
>
> Hello Fandom Support,
>
> I am building a non-production portfolio project called Product Variant Resolver. I would like written
> permission to perform limited,read-only automated access to text release tables on the Hot Wheels Wiki.
> The purpose is to stage source observations for human review;the project will not download images/video,
> bypass access controls,solve CAPTCHAs,or present wiki rows as verified official Mattel products.
>
> Proposed initial test:at most three GET requests,one at a time,at least five seconds apart,with a descriptive
> User-Agent containing my contact information,caching,JSON/GZip and MediaWiki`maxlag=1`. If the test is allowed
> and successful,I would request separate approval before any larger batch. The longer-term research target is
> up to approximately3,000 deduplicated source-release observations,not3,000 simultaneous requests or verified
> products.
>
> Please confirm whether automated access is permitted;which exact API/Export endpoints may be used;any rate,
> volume,retention or redistribution restrictions;required attribution/license terms;whether page text may be
> stored in a public GitHub portfolio repository;and whether the requested use has an expiry or review date.
>
> Project repository:[repository URL]
> Contact:[name and email]

## How to evaluate a response

The reply must clearly identify the sender/organization,date,allowed purpose,endpoints,content type,request
or rate limits,retention/redistribution/attribution requirements and expiry. “The content is CC BY-SA” alone
is not automated-access permission. A support article,community comment or general MediaWiki page is not a
project-specific approval.

Save a private original outside Git. Commit only a redacted evidence record and SHA-256 after checking that
redaction did not remove the operative permission. If permission is denied,unclear,expired or narrower than
the plan,do not proceed beyond its actual scope. Do not ask me to evade restrictions;the alternative is an
explicitly licensed bulk source or a lawfully obtained local export with provenance.

## What approval would unlock

Written permission would unlock only the next planning gate:verify Hot Wheels Wiki's current license/robots,
freeze exact endpoints/pages/revisions and ask the owner to approve a maximum three-request canary. It would
not automatically authorize the500/1,500/3,000-row batches,PostgreSQL writes or canonical promotion.
