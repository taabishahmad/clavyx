<div align="center">

# CLAVYX

**Find the key your conclusion rests on.**

An AI thinking partner that reads any argument, surfaces the hidden assumptions it depends on, finds the *minimal set* the conclusion cannot survive without, and answers with the strongest fair opposing case.

</div>

---

## What this is

I built CLAVYX because the hardest part of thinking well is not finding arguments, it is seeing the ones you have already accepted without noticing. Most assistants help you make your case. CLAVYX does the opposite, on purpose: it shows you the skeleton under your own reasoning, finds the single stone the whole thing rests on, lets you stress test it, and gives you the strongest honest version of the other side.

It is both a polished product and my final year research project. Behind the interface is a defined task, a real algorithm for the minimal sufficient assumption set, and a design that is honest about what it measures.

## Features

- **Assumption excavation** — surfaces the unstated premises an argument silently depends on.
- **Keystone (minimal sufficient set)** — a greedy, entailment based search that reduces the assumptions to the few the conclusion genuinely needs.
- **Influence ordering** — ranks assumptions from most to least load bearing, shown as an ordering rather than a false precise number.
- **Interactive stress test** — turn an assumption off and watch the estimated support for the conclusion move.
- **Fair opposing case** — a steelman aimed at the keystone, never a strawman.
- **Evidence ledger** — the proof that would rationally change your mind, tied to the assumption it tests.
- **Full accounts system** — sign up, sign in, password reset, optional two factor authentication, profile and account deletion.
- **Saved history and dashboard**, plus a small **admin** area.
- **Many pages**: landing, how it works, learn, pricing, about, terms, privacy, and the whole signed in app.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy 2.0
- **Database:** SQLite (zero setup, a single file)
- **Frontend:** server rendered Jinja2 templates with a hand built design system, vanilla JavaScript for the live analyzer (no build step)
- **AI layer:** a pluggable provider. Runs fully offline on CPU by default, and upgrades to OpenAI, Groq, or Anthropic the moment you add an API key.

## Security

Security was a first class requirement, not an afterthought:

- Passwords hashed with PBKDF2 SHA256 and a per user salt (bcrypt or Argon2 are drop in replacements).
- Sessions carried in a signed JWT inside an httpOnly cookie, so page scripts can never read the token.
- CSRF protection on every state changing request using the double submit pattern.
- Strict server side validation on all input with Pydantic. The client is never trusted.
- Account lockout after repeated failed logins, plus in memory rate limiting.
- A strict Content Security Policy and a full set of security headers on every response.
- Basic prompt injection defence in the AI layer: user content is fenced and labelled as data, never as instructions.

## Running it locally

You need Python 3.10 or newer. It runs on CPU, no GPU required.

```bash
# 1. clone and enter the project
cd clavyx

# 2. create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. install dependencies
pip install -r requirements.txt

# 4. create your environment file
cp .env.example .env        # on Windows: copy .env.example .env
#   then open .env and set CLAVYX_SECRET_KEY to a long random string:
#   python -c "import secrets; print(secrets.token_hex(32))"

# 5. run it
uvicorn app.main:app --reload
#   or simply: python run.py
```

Now open **http://127.0.0.1:8000** in your browser, create an account, and analyse your first argument.

## Making yourself an admin

Sign up in the app first, then run:

```bash
python make_admin.py your@email.com
```

You will then see the Admin link in the sidebar.

## Turning on a real AI model (optional)

Out of the box CLAVYX uses a built in offline engine so it works with no key and no GPU. To get real model quality, open `.env`, set `CLAVYX_LLM_PROVIDER` to `openai`, `groq`, or `anthropic`, and paste in the matching API key. Groq has a fast, generous free tier and is a great choice for a student project. Restart the server and the dashboard will show which engine is active.

## Adding the images

The design references a few illustrations. Drop your generated images into `app/static/img/` using the exact file names listed in `app/static/img/README.txt`. If an image is missing, the page shows a tasteful stone coloured placeholder instead, so nothing ever breaks. The brand logo is an SVG at `app/static/logo.svg` and needs no image file.

## Project layout

```
clavyx/
  app/
    main.py            application entry point, middleware, error handling
    config.py          settings from environment variables
    database.py        SQLAlchemy engine and session
    models.py          User and Analysis tables
    schemas.py         input validation
    security.py        hashing, JWT, CSRF, rate limiting, lockout
    deps.py            shared request helpers
    routers/           pages, auth, app views, api, admin
    services/          the AI layer and the reasoning pipeline
      pipeline.py      the seven stage pipeline and the minimal set algorithm
      llm_provider.py  offline engine plus OpenAI, Groq, Anthropic
      nli.py           entailment check used by the keystone search
    templates/         all the pages
    static/            css, js, logo, images
  requirements.txt
  run.py
  make_admin.py
```

## A note on honesty

The support figure in the stress test is a model estimate, shown to make dependency tangible. It is never presented as a measured probability. Where a model grades an output, the intent is to first check its grades against human judgement. This is the same care I am carrying into the research write up.

## Author

**Tabish Ahmad** — final year Computer Science, International Islamic University, Islamabad.
Built with **Haris Bin Habib**, supervised by **Dr. Syed Saqlain**.

- Email: tabishahmad2021@gmail.com
- GitHub: https://github.com/taabishahmad
- LinkedIn: https://linkedin.com/in/taabishahmad

## License

Released for academic and demonstration purposes as part of a final year project.
