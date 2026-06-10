# Spec: Agentic DevOps Company & Product Website

## Background
Build a fast-loading, statically generated company website to introduce the organization and its flagship product—an agentic software engineering service that automates DevOps, CI/CD, and development workflows. The site targets prospective clients, partners, and developers seeking to understand the company’s mission and product capabilities. Content will be managed via static files updated by developers, with a React frontend (SSG) and a Python FastAPI backend serving assets and handling contact form submissions. The visual theme should draw direct inspiration from the sleek, high-performance aesthetics of Hyperliquid, Lighter, and Pendle.

## Use cases
1. **View Company Overview:** A visitor lands on the Home page and navigates to the About page to read the company’s mission, background, and team context.
2. **Explore Product Capabilities:** A visitor accesses the Product and Features pages to understand how the agentic service handles DevOps, CI/CD, and development end-to-end.
3. **Submit Contact Inquiry:** A visitor fills out the Contact form, which triggers both an email notification and a Google Form submission.
4. **Navigate & Load Pages Quickly:** A visitor interacts with the site across devices, experiencing fast initial loads and seamless routing between Home, About, Features, Contact, and Product pages.

## Functional requirements
1. The site shall render exactly five core pages: Home, About, Features, Contact, and Product.
2. The frontend shall be built with React and use Static Site Generation (SSG) to pre-render all pages at build time.
3. All page content (text, images, layout structure) shall be sourced from static files (e.g., Markdown/JSON/YAML) updated by developers; no CMS or admin panel shall be included.
4. The Contact form shall accept name, email, and message fields.
5. Upon successful submission, the form shall trigger two actions: send an email notification and append the data to a designated Google Form.
6. The FastAPI backend shall serve static assets, handle the contact form POST request, validate payloads, and return appropriate success/error responses.
7. The site shall display the company logo prominently in the header/navigation area.
8. The visual design shall reference the layout patterns, typography, spacing, and component styling of Hyperliquid, Lighter, and Pendle websites.
9. There a need to make the whole website to have a dry run mode to do demos.

## Non-functional requirements
1. **Performance:** Initial page load time shall be under 2 seconds on a standard 4G connection; Lighthouse performance score ≥ 90.
2. **SEO:** All pages shall include semantic HTML, meta tags, Open Graph tags, and a `sitemap.xml` generated at build time.
3. **Accessibility:** Core pages shall meet WCAG 2.1 AA standards (color contrast, keyboard navigation, ARIA labels, focus states).
4. **Security:** Contact form submissions shall be validated server-side; FastAPI shall enforce strict JSON content-type checking; HTTPS shall be enforced across all endpoints.
5. **Compliance:** The site shall include a Privacy Policy and Terms of Service section/page, with cookie consent management if analytics or third-party scripts are added.
6. **Reliability:** The backend shall handle contact form submissions with retry logic or idempotency keys to prevent duplicate submissions during network failures.
7. **Design Consistency:** The site shall default to a dark theme with clean gradients, modern sans-serif typography, and responsive breakpoints matching the referenced DeFi/crypto platform aesthetics.

## Technology
- **Frontend:** React with Static Site Generation (SSG) — *binding constraint*
- **Backend:** Python FastAPI — *binding constraint*
- **Runtime:** Python 3.12 or 3.13 (recommended per 2026 ecosystem stability)
- **Content/Data:** Static files (Markdown/JSON/YAML) — *binding constraint*
- **Integrations:** Email delivery service, Google Forms API
- **Deployment Target:** Cloud-hosted static frontend + FastAPI backend — *Tech Lead to select specific hosting/platform*
- **Notes:** FastAPI’s default strict JSON content-type validation and auto-generated OpenAPI docs shall be utilized. The Tech Lead shall select the specific SSG approach (e.g., Next.js, Vite+SSG, Astro), email provider, and hosting infrastructure.

## Out of scope
- User authentication / login / registration
- Dynamic content management system (CMS) or admin dashboard
- Blog / news / press section
- Multi-language / i18n support
- E-commerce / pricing checkout flows
- Real-time chat or live support widgets
- Analytics dashboard or user behavior tracking
- Database or persistent data storage

## Open questions
1. Which email service provider should be used for contact form notifications?
2. What is the exact Google Form URL/ID for contact submissions?
3. Should the site default to dark mode, or provide a light/dark toggle?
4. Are there specific brand guidelines (hex colors, fonts, logo variants) beyond the referenced sites?
5. What is the target deployment environment / hosting provider for the FastAPI backend?
6. Should the contact form include a honeypot or CAPTCHA to prevent spam?
7. What is the expected monthly traffic volume to inform CDN and backend scaling configuration?
