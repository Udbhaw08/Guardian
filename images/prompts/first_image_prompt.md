### Plain Text Prompt

Create an ultra-clean futuristic cybersecurity analytics dashboard UI in a premium glassmorphism style, 16:9 aspect ratio. Background is a solid light cool gray (#D9DDE1). A large floating rounded rectangle dashboard occupies approximately 90% of the canvas with an extra-thick white border (16–20 px), a secondary inner border, 42 px corner radius, subtle ambient shadow, and soft frosted-glass appearance.

The dashboard is divided into three major sections: a narrow left sidebar (8%), a large central workspace (68%), and a right utility sidebar (24%).

Top navigation bar spans full width with frosted white glass effect. Left side contains a circular white logo button with a black geometric stacked-triangle logo. Next is an elongated rounded search field labeled "Search..." with a very light gray fill (#F6F6F6), followed by circular Search and Microphone icon buttons. Right side includes a mint-green rounded pill labeled "Online support", a circular notification bell, the user name "Nika Meyer", and a circular female profile photo aligned to the far right.

### Left Sidebar

Minimal vertical navigation centered with circular outline icons:

* Home
* Grid/apps
* Messages
* Calendar
* Activity/history
* Settings

Large vertical spacing between icons.

Bottom section contains:

* Dark/light mode toggle inside a rounded vertical capsule.
* Circular profile avatar.
* Logout icon.

Sidebar background is transparent white with subtle blur.

---

### Main Workspace

Large white rounded card with approximately 32 px corner radius.

Top heading:
**Verification stats**
Very large bold black sans-serif (Inter/SF Pro Display style), approximately 68–72 px visual weight.

Right of heading:
Two KPI widgets horizontally aligned.

Widget 1:

* Thin circular outlined clock icon.
* Large number **124**
* Caption:
  "You have been online"
  "Hours per month"

Widget 2:

* Thin outlined globe icon.
* Large number **315**
* Caption:
  "This month you visited"
  "Sites"

Below heading is a horizontal pill navigation:

All
Activity (active)
Protection
Update
Resources
+
All pills have white background except active pill which is pastel mint (#D8F2EE).

---

### Primary Analytics Card

Very large rounded rectangle with pale cyan background (#DDF4F3).

Title:
**Your activity**

Upper controls:
Tiny timeline labels:
More
1d
7d
1month (active)
6m
1y
September

Upper-right:
Tiny download icon.
Small filter button.
Black/gray Activity level toggle.

Left information panel:

Rounded translucent card.

Title:
Your device

Small device icons:
phone
tablet
desktop

Below:
Unconfirmed login attempts

Two pastel action buttons:
View more
View more

Right visualization:

Histogram composed of rounded vertical blocks.

Bars vary in height.

Colors:

Light gray

Medium gray

Dark gray

Black

Some bars contain tiny pastel indicator dots.

Dates beneath bars:

22 Sept
23 Sept
24 Sept
25 Sept
26 Sept
27 Sept
28 Sept
29 Sept
30 Sept

Far right vertical floating circular action buttons:

Black analytics icon

White timer icon

White trend icon

White three-dot menu

Bottom-right contains a curved white scrollbar.

---

### Bottom Left Card

Title:
Most used

Subtitle:
5 most visited resources

Five rounded vertical progress bars.

Percentages:

30%

72%

52%

76%

27%

Pastel colors:

Mint

Lavender

Black

Light teal

Light purple

Circular social icons underneath:

Threads

Instagram

X

Behance

Dribbble

---

### Bottom Center Card

Title:
Protection

Large rounded analytics card.

Upper left:
Black pill:
More

Main label:
Account protection

Subtitle:
Increased by 23%

Large pastel cyan section displaying:

23%

Row of rounded triangular indicators.

Bottom section:

Black rounded rectangle.

White waveform chart.

Label:
Verification speed

Increase by 17%

Large percentage:

17%

Small More button.

---

### Bottom Right Card

Title:
Update

Subtitle:
New updates to our system

Rounded white card containing:

Abstract colorful holographic AI head sculpture.

Material:
Glossy iridescent plastic with metallic holographic reflections.

Colors:
Purple
Turquoise
Mint
Pink
Blue
Orange

Head faces slightly left.

No visible facial features.

Top-left floating heart icon.

Top-right circular share icon.

Bottom overlay:

Verification by AI

White Read button.

---

### Right Sidebar

Top:

Large outlined rounded square frame.

Inside:
Minimal gray human avatar illustration.

Top-right floating camera button.

Below:

Large title:
Add user

Subtitle:
You can add 2 users

Below:

Horizontal rounded avatar group.

Three profile photos.

Small overflow indicator.

Text:

You have added 8 users

Rounded View all button.

---

Resources Section

Title:
Resources

14 added

Four rounded switch rows:

Snapchat
Toggle OFF (black)

Behance
Toggle ON (mint)

Dribbble
Toggle ON (mint)

Instagram
Toggle LIMITED (lavender)

Each row has:
three-dot menu
rounded toggle switch

Bottom:

View all dropdown

Add button

---

Bottom Premium Card

Rounded black glass card.

Progress:

17/60 resources

White dotted progress arc.

Text:

Expand your possibilities

Upgrade your plan and expand your account

More info

Bottom center rounded Add button.

---

### Style

Modern enterprise SaaS dashboard

Glassmorphism

Apple-inspired UI

Minimalism

Premium fintech aesthetic

Huge rounded corners

Soft ambient shadows

Thin gray outlines

Large whitespace

Perfect alignment

Vector UI

Pastel mint accents

Black typography

White surfaces

Subtle blur

Ultra-clean interface

Inter / SF Pro Display typography

Flat icons with 2 px outline

Pixel-perfect spacing

---

```json
{
  "scene": {
    "type": "Cybersecurity verification dashboard",
    "aspect_ratio": "16:9",
    "background": {
      "color": "#D9DDE1"
    },
    "container": {
      "color": "#FFFFFF",
      "glass": true,
      "corner_radius": 42,
      "outer_border": "18px white",
      "inner_border": "2px light gray",
      "shadow": "soft ambient"
    }
  },
  "layout": {
    "left_sidebar": {
      "width": "8%",
      "icons": [
        "home",
        "grid",
        "messages",
        "calendar",
        "activity",
        "settings"
      ],
      "bottom": [
        "theme toggle",
        "profile avatar",
        "logout"
      ]
    },
    "header": {
      "logo": "black geometric triangle mark",
      "search": true,
      "voice": true,
      "support": "Online support",
      "notification": true,
      "user": "Nika Meyer"
    },
    "center": {
      "title": "Verification stats",
      "stats": [
        {
          "label": "You have been online",
          "value": 124
        },
        {
          "label": "This month you visited",
          "value": 315
        }
      ],
      "tabs": [
        "All",
        "Activity",
        "Protection",
        "Update",
        "Resources",
        "+"
      ],
      "activity_chart": {
        "background": "#DDF4F3",
        "type": "rounded histogram",
        "dates": [
          "22 Sept",
          "23 Sept",
          "24 Sept",
          "25 Sept",
          "26 Sept",
          "27 Sept",
          "28 Sept",
          "29 Sept",
          "30 Sept"
        ]
      },
      "cards": [
        "Most used",
        "Protection",
        "Update"
      ]
    },
    "right_sidebar": {
      "add_user": true,
      "resources": [
        "Snapchat",
        "Behance",
        "Dribbble",
        "Instagram"
      ],
      "premium_card": true
    }
  },
  "palette": {
    "white": "#FFFFFF",
    "black": "#111111",
    "mint": "#D8F2EE",
    "cyan": "#DDF4F3",
    "gray": "#D9DDE1",
    "lavender": "#E8D8F7"
  },
  "typography": {
    "font": "Inter",
    "heading": "extra bold",
    "body": "medium"
  },
  "effects": {
    "glassmorphism": true,
    "soft_blur": true,
    "subtle_shadows": true,
    "rounded_ui": true
  }
}
```

```yaml
style: Premium glassmorphism cybersecurity dashboard
aspect_ratio: "16:9"

background:
  color: "#D9DDE1"

container:
  color: white
  frosted_glass: true
  border:
    outer: 18px white
    inner: 2px light_gray
  radius: 42
  shadow: soft

layout:
  left_sidebar:
    navigation:
      - Home
      - Grid
      - Messages
      - Calendar
      - Activity
      - Settings
    footer:
      - Theme toggle
      - Profile
      - Logout

  header:
    logo: geometric_black
    search: true
    microphone: true
    support_button: Online support
    notifications: true
    user: Nika Meyer

  main:
    title: Verification stats
    statistics:
      - Online hours: 124
      - Visited sites: 315
    tabs:
      - All
      - Activity
      - Protection
      - Update
      - Resources
      - "+"
    activity_panel:
      title: Your activity
      chart: rounded_histogram
      controls:
        - More
        - 1d
        - 7d
        - 1month
        - 6m
        - 1y
        - September
    cards:
      - Most used
      - Protection
      - Update

  right_sidebar:
    add_user: true
    resources:
      - Snapchat
      - Behance
      - Dribbble
      - Instagram
    premium_upgrade: true

colors:
  primary: "#111111"
  white: "#FFFFFF"
  mint: "#D8F2EE"
  cyan: "#DDF4F3"
  lavender: "#E8D8F7"
  gray: "#D9DDE1"

typography:
  font: Inter
  headings: ExtraBold
  body: Medium

visual_style:
  glassmorphism: true
  apple_ui: true
  enterprise: true
  pastel_accents: true
  soft_shadows: true
  ultra_clean_spacing: true
```
