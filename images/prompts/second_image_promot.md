### Plain Text Prompt

Create a modern SaaS logistics analytics dashboard UI in a clean minimalist style. Canvas ratio 16:9. Centered large white dashboard card with 24 px rounded corners and a very soft gray background (#F3F4F2). Subtle floating shadow beneath the card with large blur radius. Overall layout split vertically into two equal columns.

Top navigation bar with white background. Left side contains a small rounded square black logo with a white abstract icon followed by the brand name **Sypher** in bold black sans-serif. Horizontal navigation links centered: Dashboard (active with black underline), Financials, Customers, Fleet, Reports, Insights, Employees in medium gray. Right side contains a white outlined button labeled "Generate Report" and a small circular profile avatar aligned to the far right.

Below the navigation is a thin status strip with light gray divider. Left side shows a small calendar icon and text "Changes: Last month (Jul 20 – Aug 20)". Center shows "Last update: 3 min ago". Far right contains "Manage layout" with a small gear icon.

Left column begins with section title **Deliveries** in bold black. Three equal statistic cards aligned horizontally:

* Fleet Utilization: 95.1% with multiple vertical green bars of equal width.
* On-Time Delivery Rate: 97.9% with a segmented horizontal bar transitioning yellow to lime to green.
* Total Deliveries: 1,352 with small green "+3.5%" and a thin green upward trend sparkline.

Middle-left large analytics panel titled **Revenue and costs**. White card with a multi-line chart over a faint gray grid. Three lines:

* Bright green revenue line.
* Black net profit line.
* Pink-red costs line.
  Include translucent green area fill beneath the revenue line. A floating tooltip near the center displays:
  Revenue $11,177,
  Net profit $9,050,
  Costs $2,127,
  using colored square markers matching each line. Bottom-left legend uses green, pink-red, and black rounded markers labeled Revenue, Costs, Net profit. Bottom-right contains a small gray toggle labeled "Vs. previous period".

Bottom-left contains two equal cards:
First card titled **Balance and costs** with cash balance "$126K", vertical green and pink-red bar chart, black dotted trend line above bars, target label "$100K".
Second card titled **Costs by category** with a horizontal segmented green-to-yellow progress indicator above a category table. Categories: Fuel, Driver salaries, Vehicle maintenance, Warehousing, Insurance, Tech & software. Right aligned values and percentages. Thin dotted separators between rows.

Right column begins with title **Invoices**. Three KPI blocks aligned horizontally:

* Paid: $169K with 51.5%.
* Resent request: $95K with 29%.
* Unpaid: $64K with 19.5%.
  Below them a full-width horizontal segmented progress bar: bright green, lime green, light gray.

Below is a tab row: All, Unpaid (active with light gray rounded pill), Resent request, Paid.

Top-right search field with rounded border, magnifying glass icon, placeholder "Search", and keyboard shortcut badge.

Large invoice table beneath. Columns:
checkbox,
Company,
Issue date,
Contact,
Value.
Rows include colored circular company icons and names such as BlueHorizon Ltd., NexaCorp, StarFreight Co., Movers, Arvox Solutions, Keystone Transport, Kestrel Freight, SwiftLogix, GlobalTrade Inc., PathBlaze Inc. Dates around Aug 15–17, 2025. Contact emails. Dollar values right aligned. Three-dot action menu at the end of each row. Thin light-gray horizontal dividers between rows.

Bottom pagination area contains "Show by 10" dropdown on the left and centered pagination "1 / 4" with left/right chevrons.

Use pure white cards (#FFFFFF), very light gray borders (#ECECEC), black headings (#222222), medium gray labels (#7A7A7A), vivid green accents (#2ECC5A), lime (#B9E84C), pink-red (#F05A7A). Typography is modern geometric sans-serif similar to Inter. Flat design with subtle shadows, generous whitespace, precise spacing, crisp vector charts, no gradients except chart fills, professional enterprise dashboard appearance.

---

```json
{
  "style": "Modern SaaS analytics dashboard",
  "aspect_ratio": "16:9",
  "background": {
    "color": "#F3F4F2",
    "card": {
      "color": "#FFFFFF",
      "radius": 24,
      "shadow": "soft large blur"
    }
  },
  "layout": {
    "type": "two-column",
    "header": {
      "brand": "Sypher",
      "nav": [
        "Dashboard",
        "Financials",
        "Customers",
        "Fleet",
        "Reports",
        "Insights",
        "Employees"
      ],
      "active": "Dashboard",
      "button": "Generate Report",
      "avatar": true
    },
    "status_bar": {
      "left": "Changes: Last month (Jul 20 – Aug 20)",
      "center": "Last update: 3 min ago",
      "right": "Manage layout"
    },
    "left_column": {
      "deliveries": {
        "cards": [
          {
            "title": "Fleet Utilization",
            "value": "95.1%",
            "chart": "green vertical bars"
          },
          {
            "title": "On-Time Delivery Rate",
            "value": "97.9%",
            "chart": "yellow-lime-green segmented bar"
          },
          {
            "title": "Total Deliveries",
            "value": "1,352",
            "change": "+3.5%",
            "chart": "green sparkline"
          }
        ]
      },
      "revenue_panel": {
        "title": "Revenue and costs",
        "chart": {
          "lines": [
            "green revenue",
            "black net profit",
            "pink-red costs"
          ],
          "grid": true,
          "tooltip": true,
          "legend": true
        }
      },
      "bottom_cards": [
        {
          "title": "Balance and costs",
          "chart": "vertical bars with dotted trend"
        },
        {
          "title": "Costs by category",
          "chart": "horizontal segmented progress",
          "categories": [
            "Fuel",
            "Driver salaries",
            "Vehicle maintenance",
            "Warehousing",
            "Insurance",
            "Tech & software"
          ]
        }
      ]
    },
    "right_column": {
      "title": "Invoices",
      "kpis": [
        "Paid",
        "Resent request",
        "Unpaid"
      ],
      "progress": "segmented horizontal bar",
      "tabs": [
        "All",
        "Unpaid",
        "Resent request",
        "Paid"
      ],
      "search": true,
      "table": {
        "columns": [
          "Company",
          "Issue date",
          "Contact",
          "Value"
        ],
        "pagination": true
      }
    }
  },
  "colors": {
    "primary_green": "#2ECC5A",
    "lime": "#B9E84C",
    "pink_red": "#F05A7A",
    "black": "#222222",
    "gray": "#7A7A7A",
    "border": "#ECECEC"
  },
  "typography": {
    "font": "Inter",
    "style": "clean geometric sans-serif"
  }
}
```

```yaml
style: Modern SaaS logistics analytics dashboard
aspect_ratio: "16:9"

background:
  color: "#F3F4F2"
  dashboard_card:
    color: "#FFFFFF"
    radius: 24
    shadow: soft_large

header:
  brand: Sypher
  active_navigation: Dashboard
  navigation:
    - Dashboard
    - Financials
    - Customers
    - Fleet
    - Reports
    - Insights
    - Employees
  action_button: Generate Report
  avatar: circular

status_bar:
  left: "Changes: Last month (Jul 20 – Aug 20)"
  center: "Last update: 3 min ago"
  right: "Manage layout"

layout:
  columns: 2

left_column:
  deliveries:
    - Fleet Utilization
    - On-Time Delivery Rate
    - Total Deliveries
  revenue_chart:
    lines:
      - green
      - black
      - pink_red
    grid: true
    tooltip: true
    legend: true
  bottom_cards:
    - Balance and costs
    - Costs by category

right_column:
  title: Invoices
  summary:
    - Paid
    - Resent request
    - Unpaid
  segmented_progress: true
  tabs:
    - All
    - Unpaid
    - Resent request
    - Paid
  search_box: true
  invoice_table:
    columns:
      - Company
      - Issue date
      - Contact
      - Value
    pagination: true

colors:
  primary_green: "#2ECC5A"
  lime: "#B9E84C"
  pink_red: "#F05A7A"
  text: "#222222"
  secondary_text: "#7A7A7A"
  border: "#ECECEC"

typography:
  font: Inter
  weight: clean_modern
  spacing: generous

lighting:
  flat_ui
  soft_shadow
  crisp_vector_rendering
```
