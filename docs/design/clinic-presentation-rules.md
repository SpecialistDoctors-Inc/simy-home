# Clinic page presentation rules

The shared pricing reference is defined in `site/hp-readable.css`.

- Use `.group` for category rows, row headings with `small` for supporting text, and the same cell padding and table borders in every category.
- Use `.price` and `.tax` for every monthly price, including optional services. Do not add per-option font sizes or promotional colors.
- A common option price spans both service columns. Label it as an additional charge, never a plan total.
- Supporting photos remain inside the row-heading column and do not change the table tracks.
- Keep text, borders, and category hierarchy consistent when adding content. Verify the rendered desktop and mobile layout before publishing.

## Service story

Introduce three benefits together, then repeat the same chapter heading, number,
spacing and anchor pattern in order: security, self-directed improvement and
editing, Google Maps and AI discovery. Keep the actual editing experience within
chapter 02. Follow the three benefits with migration steps and plan selection.
Do not insert an unrelated feature or change the meaning of the chapter numbers.
Keep the existing comic assets. A diagnosis download control appears only while
its report is in view and must not obscure the service story.

Reference perspectives (our interpretation, not proposals or endorsements):
- Japan: Yugo Nakamura / tha, interaction as experience: https://tha.jp/
- International: Vitaly Friedman, clear complex interfaces: https://www.smashingmagazine.com/author/vitaly-friedman/
- United States: Brad Frost, coherent systems from existing components: https://atomicdesign.bradfrost.com/chapter-2/

## Message order
- Lead each chapter with the service benefit and visual, then concrete capabilities, then supporting statistics. The MEO/GEO survey follows the image and service panels.
- Explain migration before the plan CTA. Pricing headings introduce plan selection rather than repeating the security chapter. Keep DOM and visual reading order identical on mobile and desktop.

## Editorial hierarchy
- Use a shared 48px desktop / 20px mobile chapter gutter. Avoid nested rounded cards for explanatory content.
- Each chapter has one focal point: security response time, working update preview, or discovery visual. Keep statistics visually secondary.
- MEO/GEO pairs its visual with service descriptions on wide screens; narrow screens read visual, services, then survey. Retain all existing imagery and functional forms.
