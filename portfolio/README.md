# Prince Adenola Adegbesan – portfolio website

A static website: plain HTML pages, no build step, no dependencies.

## Contents
- `index.html` – homepage
- `facilitation.html`, `speaking.html`, `enquire.html`
- `programme-ai-governance.html`, `programme-responsible-adoption.html`, `programme-trust-privacy.html`
- `case-study-iso-42001.html`
- `assets/` – photos, logos, videos, case-study and certificate PDFs
- `vercel.json` – clean URLs on Vercel (e.g. /speaking instead of /speaking.html)
- `sitemap.xml`, `robots.txt`

## Deploy on Vercel
1. The site lives in the `portfolio/` folder of the `IKONETU-PLATFORM-` repository. (It can also be moved to the root of its own repository, e.g. `adenola-portfolio-site`; then skip the Root Directory setting below.)
2. On vercel.com: Add New → Project → import the repository.
3. Root Directory: `portfolio`. Framework preset: **Other**. Build command: leave empty. Output directory: leave empty.
4. Deploy. Then in Project → Settings → Domains, add `adenolaadegbesan.co.uk` and `www.adenolaadegbesan.co.uk` and set the DNS records Vercel shows at your domain registrar.

## Deploy anywhere else
Upload every file and the `assets` folder to the web root of any host. Without Vercel, links still work using the `.html` names.

## Enquiry form
The form on `enquire.html` sends to Formspree (`https://formspree.io/f/meaajyep`). To change it, edit `FORMSPREE_ID` near the bottom of `enquire.html` and the form's `action` attribute.
