# Competitive Analysis: Dewey vs Leidos IQ CRM (Intranet Quorum)

## Executive Summary

**Leidos IQ CRM (Intranet Quorum)** is the dominant incumbent in the government constituent relationship management market, serving 65% of the U.S. Congress, 50% of U.S. Governors, and 100+ federal/state/local agencies. **Dewey** is a modern, AI-native platform designed to compete in this space with superior automation, analysis, and user experience.

This analysis identifies key feature gaps, competitive advantages, and strategic recommendations.

---

## Market Position

| Metric | Leidos IQ | Dewey |
|--------|-----------|-------|
| **Market Share (Congress)** | ~65% | 0% (new entrant) |
| **Years in Market** | 20+ years | New |
| **Pricing** | $1,860+/month/office | TBD |
| **FedRAMP Authorization** | Yes (FedRAMP Moderate) | Planned |
| **Target Customers** | Congress, Governors, State/Local | Same + Private Sector |

---

## Feature Comparison Matrix

### Core CRM & Contact Management

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Contact database | ✅ Full | ✅ Full | Parity |
| Custom fields | ✅ Yes | ✅ Yes | Parity |
| Contact tags/categories | ✅ Yes | ✅ Yes | Parity |
| Contact merge/dedup | ✅ Yes | ✅ Yes | Parity |
| Contact timeline/history | ✅ Yes | ✅ Yes | Parity |
| Affiliation codes | ✅ Yes | ⚠️ Via tags | Minor gap - consider dedicated affiliation system |
| Geographic/district data | ✅ Built-in | ⚠️ Basic address | **GAP: Need district lookup integration** |
| Voter file integration | ✅ Likely (via LegiStats) | ❌ No | **GAP: Need voter file matching** |

### Message Management

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Email intake | ✅ Yes | ✅ Yes (Graph API, IMAP) | Parity |
| Form submissions | ✅ Yes | ✅ Yes (drag-drop builder) | **Dewey advantage** |
| Physical mail logging | ✅ Yes | ❌ No | **GAP: Need manual mail entry** |
| Fax intake | ✅ Yes | ❌ No | **GAP: Consider fax-to-email integration** |
| Social media messages | ✅ Integrated | ❌ No | **MAJOR GAP** |
| Bulk email filtering | ⚠️ Weak (user complaints) | ✅ Campaign detection | **Dewey advantage** |
| Message assignment | ✅ Yes | ✅ Yes | Parity |
| Response tracking | ✅ Yes | ✅ Yes | Parity |

### AI & Automation

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| AI tone/sentiment analysis | ❌ None evident | ✅ Multi-tone detection | **MAJOR Dewey advantage** |
| Entity extraction | ❌ No | ✅ Yes (people, orgs, locations, topics) | **MAJOR Dewey advantage** |
| Auto-categorization | ❌ Manual/keyword only | ✅ AI-suggested with confidence scores | **MAJOR Dewey advantage** |
| Response suggestions | ❌ No | ✅ AI-generated | **MAJOR Dewey advantage** |
| Urgency scoring | ❌ No | ✅ Yes (0-1 scale) | **MAJOR Dewey advantage** |
| Campaign detection | ❌ No | ✅ Template matching | **MAJOR Dewey advantage** |
| Workflow automation | ✅ Yes (templates) | ✅ Yes (rule-based triggers) | Parity |
| Auto-reply | ⚠️ Limited | ✅ Template-based | Dewey advantage |

### Legislative Features

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| **LegiStats module** | ✅ Full | ❌ None | **CRITICAL GAP** |
| Bill tracking | ✅ Yes | ❌ No | **CRITICAL GAP** |
| Vote record tracking | ✅ Yes | ❌ No | **CRITICAL GAP** |
| Member position tracking | ✅ Yes | ⚠️ Via categories/stance | Partial |
| Bill-to-message linking | ✅ Yes | ❌ No | **CRITICAL GAP** |
| Demographic analysis | ✅ Yes | ⚠️ Basic analytics | GAP |

### Constituent Services / Casework

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| **Services module** | ✅ Full | ❌ None | **CRITICAL GAP** |
| Case management | ✅ Yes | ❌ No | **CRITICAL GAP** |
| Flag requests | ✅ Built-in template | ❌ No | GAP |
| Tour requests | ✅ Built-in template | ❌ No | GAP |
| Agency referrals | ✅ Yes | ❌ No | GAP |
| Service status tracking | ✅ Yes | ❌ No | **CRITICAL GAP** |
| Extended workflow (external parties) | ✅ Yes | ❌ No | GAP |

### Outreach & Email Marketing

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Newsletter builder | ✅ In-platform | ✅ Email template builder | Parity |
| Email campaigns | ✅ Yes | ✅ Yes | Parity |
| Survey creation | ✅ Yes | ✅ Forms with NPS/rating fields | Parity |
| Form links (pre-identified) | ⚠️ Unknown | ✅ Yes (secure tokens) | Possible Dewey advantage |
| SMS/texting | ✅ Yes | ❌ No | **GAP** |
| Targeted mailing lists | ✅ Yes | ⚠️ Basic filtering | Minor gap |
| Town hall management | ✅ Yes | ❌ No | GAP |

### Events & Scheduling

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| **Events module** | ✅ Full | ❌ None | **MAJOR GAP** |
| Calendar management | ✅ Yes | ❌ No | **MAJOR GAP** |
| Eventbrite integration | ✅ Yes | ❌ No | GAP |
| Appointment scheduling | ✅ Yes | ❌ No | **MAJOR GAP** |
| Outlook sync | ✅ Yes | ❌ No | GAP |

### Boards & Committees

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| **Boards module** | ✅ Full | ❌ None | GAP (niche feature) |
| Commission tracking | ✅ Yes | ❌ No | GAP |
| Nomination tracking | ✅ Yes | ❌ No | GAP |
| Seat assignments | ✅ Yes | ❌ No | GAP |

### Social Media

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Facebook integration | ✅ Yes | ❌ No | **MAJOR GAP** |
| Twitter/X integration | ✅ Yes | ❌ No | **MAJOR GAP** |
| Instagram integration | ✅ Yes | ❌ No | **MAJOR GAP** |
| YouTube integration | ✅ Yes | ❌ No | GAP |
| Social message storage | ✅ Yes | ❌ No | **MAJOR GAP** |
| Social analytics | ✅ Yes | ❌ No | **MAJOR GAP** |
| In-platform response | ✅ Yes | ❌ No | **MAJOR GAP** |

### Analytics & Reporting

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Pre-built reports | ✅ Yes | ✅ Yes | Parity |
| Custom reports | ✅ Yes | ⚠️ Basic | Minor gap |
| Staff productivity metrics | ✅ Yes | ⚠️ Limited | GAP |
| Constituent demographics | ✅ Yes | ⚠️ Limited | GAP |
| BI tool integration | ⚠️ Unknown | ✅ OData for Power BI/Tableau | Possible Dewey advantage |
| Real-time dashboard | ⚠️ Unknown | ✅ Yes | Possible Dewey advantage |
| Sentiment trends | ❌ No | ✅ Yes | **Dewey advantage** |
| Geographic heat maps | ❌ No | ⏳ Planned | **MAJOR Dewey advantage (planned)** |
| AI targeting recommendations | ❌ No | ⏳ Planned | **MAJOR Dewey advantage (planned)** |
| Voter propensity visualization | ❌ No | ⏳ Planned | **MAJOR Dewey advantage (planned)** |

### Administration & Security

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Role-based access | ✅ Yes | ✅ Yes (granular permissions) | Parity |
| Azure AD SSO | ⚠️ Unknown | ✅ Yes | Possible Dewey advantage |
| API access | ⚠️ Limited | ✅ Full REST API | **Dewey advantage** |
| API key management | ⚠️ Unknown | ✅ Scoped keys, rate limiting | Possible Dewey advantage |
| Audit logging | ✅ Yes | ✅ Yes | Parity |
| FedRAMP authorization | ✅ Yes (Moderate) | ⏳ Planned | **GAP (critical for gov)** |
| Multi-tenant | ✅ Yes | ✅ Yes | Parity |
| Document library | ✅ Yes | ❌ No | GAP |

### Integrations

| Feature | Leidos IQ | Dewey | Gap Analysis |
|---------|-----------|-------|--------------|
| Microsoft Outlook | ✅ Yes | ⚠️ Email only (no calendar) | GAP |
| Microsoft 365 | ✅ Yes | ✅ Graph API | Parity |
| Eventbrite | ✅ Yes | ❌ No | GAP |
| Zapier/webhooks | ⚠️ Unknown | ✅ Yes | Possible Dewey advantage |
| Power Automate | ⚠️ Unknown | ✅ Webhooks | Possible Dewey advantage |

---

## SWOT Analysis

### Dewey Strengths
1. **AI-native architecture** - Tone detection, entity extraction, auto-categorization, response suggestions
2. **Modern tech stack** - React, FastAPI, PostgreSQL vs legacy Oracle/ASP
3. **Campaign detection** - Automatically identifies coordinated messaging
4. **Superior form builder** - Drag-drop with conditional logic, pre-identified links
5. **API-first design** - Full REST API with scoped keys, OData for BI tools
6. **Pluggable AI providers** - Claude, OpenAI, Azure OpenAI, Ollama
7. **Multi-market targeting** - Government AND private sector

### Dewey Weaknesses
1. **No legislative module** - Missing bill tracking, vote records, LegiStats equivalent
2. **No casework/services** - Critical for constituent services offices
3. **No social media integration** - IQ has Facebook, Twitter, Instagram, YouTube
4. **No events/calendar** - Missing entire module
5. **No FedRAMP authorization** - Blocker for many government customers
6. **No SMS capability** - IQ offers texting
7. **No market presence** - IQ has 20+ year incumbent advantage
8. **No physical mail/fax** - Government offices still receive these

### Dewey Opportunities
1. **AI differentiation** - IQ appears to have no AI capabilities
2. **UX modernization** - IQ has documented usability complaints
3. **Price competition** - IQ at $1,860+/month is expensive
4. **Private sector expansion** - Corporate CRM with same capabilities
5. **Developer ecosystem** - API-first enables integrations
6. **FedRAMP pursuit** - Azure Government path available

### Dewey Threats
1. **IQ's market lock-in** - 65% of Congress, long contracts
2. **Switching costs** - Data migration, staff retraining
3. **FedRAMP timeline** - 12-18 months minimum
4. **IQ feature catch-up** - Leidos could add AI features
5. **Budget cycles** - Government procurement is slow

---

## IQ Known Weaknesses (User Feedback)

Based on user reviews, IQ has documented problems:

1. **Mail filtering behind competitors** - "Filtering of incoming mail and assigning responses is behind competitors iConstituent and Fireside 21"
2. **Development team unresponsive** - "The development team did not listen to long time users (10 years plus)"
3. **Unintuitive interface** - "It could be a little difficult to use at times. It was also not intuitive to use"
4. **Search/archiving issues** - "The search function and archiving is tricky and time consuming"
5. **No real-time collaboration** - "Real-time interfaces are important when communicating amongst a large office group"
6. **Manual mail logging required** - Some implementations don't auto-import email, "defeating time saving aspects"

**Opportunity**: Dewey can differentiate on UX, modern interface, and responsive development.

---

## Strategic Recommendations

### Critical Gaps to Address (Priority 1)

These are **blockers for government market entry**:

#### 1. Legislative Module ("LegiStats")
- Bill tracking and status
- Vote record management
- Member position on legislation
- Bill-to-constituent-message linking
- Integration with Congress.gov API or equivalent data source

#### 2. Casework/Services Module
- Case types (flag requests, tours, agency referrals, etc.)
- Case status tracking (open, pending, closed)
- Agency contact management
- Case templates and workflows
- Service request forms

#### 3. FedRAMP Authorization
- Target FedRAMP Moderate via Azure Government
- 12-18 month process, start immediately
- Enables federal agency sales

### Major Gaps to Address (Priority 2)

#### 4. Social Media Integration
- Facebook, Twitter/X, Instagram at minimum
- Ingest social messages into unified inbox
- Track and respond from platform
- Social analytics
- Consider partnership with social media management tool

#### 5. Events & Calendar Module
- Event creation and management
- RSVP tracking
- Calendar sync (Outlook, Google)
- Consider Eventbrite integration or build native

#### 6. SMS/Texting
- Two-way texting capability
- Bulk SMS campaigns
- Opt-in/opt-out management
- Consider Twilio integration

### Enhancements to Existing Features (Priority 3)

#### 7. Physical Mail & Fax Support
- Manual entry interface for physical mail
- Fax-to-email integration (eFax, etc.)
- Scan/OCR workflow

#### 8. District/Geographic Data & Voter File Integration
- Integration with Census geocoding
- Congressional district lookup
- State legislative district lookup
- Demographic data enrichment

**Voter File Integration** (high value for political offices):

Voter history is public record and foundational for constituent engagement. Integration should include:

| Data Point | Source | Use Case |
|------------|--------|----------|
| Voting history | State voter files | Identify frequent vs. occasional voters |
| Party registration | State voter files | Targeting, understanding constituent base |
| Registration status | State voter files | Verify active voters in district |
| Primary participation | State voter files | Identify engaged partisans |

**Implementation Options:**
1. **Direct state file ingestion** - Purchase/obtain voter files from each state (costs vary: free to $50K per state)
2. **Commercial vendor integration** - L2, TargetSmart, Aristotle provide normalized national files with consumer data overlays
3. **Party file access** - RNC/DNC maintain enhanced files (requires party relationship)

**Recommended Approach:**
- Start with commercial vendor API (L2 or TargetSmart) for normalized data
- Match contacts by name + address or name + DOB
- Display voter score, party registration, and vote history on contact profile
- Enable filtering/segmentation by voter propensity
- Consider this a **differentiator** - AI analysis + voter data = powerful constituent intelligence

**Privacy Considerations:**
- Voter file data is public record, but handling should be transparent
- Allow constituents to opt-out of enhanced profiling
- Follow state-specific regulations on voter data use

#### 9. Document Library
- Central document storage
- Form letter templates
- Approval workflows for documents

#### 10. Staff Productivity Reporting
- Messages handled per user
- Response time metrics
- Case resolution times
- Workload distribution

#### 11. Geographic Intelligence Dashboard & AI-Powered Targeting (HIGH VALUE DIFFERENTIATOR)

This feature combines geographic visualization, voter data, AI analysis, and campaign targeting into a unified intelligence platform. **IQ does not appear to offer anything comparable.**

**Geographic Heat Map Visualization:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  District Map View                              [Zoom] [Filter] [▼] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│     ┌──────────┐                                                    │
│     │ Precinct │  ◄── Color intensity = sentiment/engagement        │
│     │   A-12   │      Click to drill down                           │
│     │  🔴 -0.3 │                                                    │
│     └──────────┘                                                    │
│           ┌──────────┐  ┌──────────┐                                │
│           │ Precinct │  │ Precinct │                                │
│           │   A-13   │  │   A-14   │                                │
│           │  🟢 +0.6 │  │  🟡 +0.1 │                                │
│           └──────────┘  └──────────┘                                │
│                                                                     │
│  Legend: 🔴 Negative  🟡 Neutral  🟢 Positive                       │
│  Layer:  [Sentiment ▼] [Voter Propensity] [Issue: Healthcare]       │
└─────────────────────────────────────────────────────────────────────┘
```

**Map Layers (toggle/overlay):**

| Layer | Data Source | Visualization |
|-------|-------------|---------------|
| Constituent sentiment | Dewey AI analysis | Red/yellow/green heat map |
| Voter propensity | Voter file (vote frequency) | Gradient by turnout likelihood |
| Issue intensity | Message categorization | Heat by volume/sentiment per issue |
| Party registration | Voter file | Color by party affiliation |
| Engagement level | Message count + recency | Activity heat map |
| Unreached voters | Voter file - contact history | Highlight gaps in outreach |

**Drill-Down Hierarchy:**
- District → County → Precinct → Census block → Individual addresses
- Click any region to zoom and see constituent list
- Aggregate statistics at each level

**AI-Powered Targeting Engine:**

The real differentiator is using AI to generate actionable targeting recommendations:

```
┌─────────────────────────────────────────────────────────────────────┐
│  AI Targeting Recommendations                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🎯 LOW-PROPENSITY VOTER OUTREACH                                   │
│  ─────────────────────────────────────────────────────────────────  │
│  "2,847 constituents voted in 2020 but skipped 2022 midterms.       │
│   Based on their past correspondence, 67% care about healthcare.    │
│   Recommend: Healthcare-focused GOTV mailer before registration     │
│   deadline."                                                        │
│                                                                     │
│  [Preview Audience] [Generate Mail Merge] [Create Campaign]         │
│                                                                     │
│  🎯 SENTIMENT RECOVERY - PRECINCT A-12                              │
│  ─────────────────────────────────────────────────────────────────  │
│  "Precinct A-12 shows -0.3 avg sentiment (district avg: +0.2).      │
│   Primary driver: 43 negative messages about road construction.     │
│   12 messages still awaiting response (avg 8 days).                 │
│   Recommend: Prioritize responses + schedule town hall in area."    │
│                                                                     │
│  [View Messages] [Draft Response Template] [Schedule Event]         │
│                                                                     │
│  🎯 ISSUE OPPORTUNITY - EDUCATION                                   │
│  ─────────────────────────────────────────────────────────────────  │
│  "Education messages up 340% this month. Sentiment: +0.7.           │
│   Constituents responding positively to your school funding vote.   │
│   847 engaged constituents have not received follow-up.             │
│   Recommend: Thank-you email campaign with newsletter signup."      │
│                                                                     │
│  [Preview Audience] [Select Template] [Launch Campaign]             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Targeting Criteria Builder:**

Allow staff to build custom segments combining:

| Dimension | Operators | Example |
|-----------|-----------|---------|
| Vote history | Voted in / missed / registered after | "Voted 2020, missed 2022" |
| Vote frequency | High/medium/low propensity | "Low propensity voters" |
| Party registration | Equals / not equals | "Registered Democrat" |
| Geography | In precinct / zip / radius | "Within 5 miles of Main St" |
| Sentiment | Positive / negative / neutral | "Negative sentiment contacts" |
| Issue/category | Has messaged about | "Contacted about healthcare" |
| Stance on issue | Supports / opposes | "Opposes tax increase" |
| Recency | Last contact within | "No contact in 6 months" |
| Engagement | Message count | "Sent 3+ messages" |
| Response status | Awaiting response | "Has unanswered message" |

**Example Targeting Queries:**

1. **GOTV for occasional voters:**
   ```
   Vote frequency = "low" AND
   Voted in = "2020 General" AND
   Geography = "District 5" AND
   Has messaged about = "any"
   → 2,847 contacts
   ```

2. **Persuasion on healthcare:**
   ```
   Issue stance = "opposes healthcare bill" AND
   Sentiment = "neutral or positive" AND
   Vote frequency = "high"
   → 423 contacts (persuadable, likely to vote)
   ```

3. **Damage control in angry precinct:**
   ```
   Geography = "Precinct A-12" AND
   Sentiment = "negative" AND
   Response status = "awaiting response"
   → 12 contacts (prioritize these)
   ```

**Integrated Campaign Actions:**

From any targeting segment, one-click actions:

| Action | Description |
|--------|-------------|
| **Generate Mail Merge** | Export to PDF for print mailers with personalized fields |
| **Email Campaign** | Send templated email via Dewey email system |
| **SMS Blast** | Send text message (requires SMS integration) |
| **Create Form Links** | Generate pre-identified survey/feedback links |
| **Export to CSV** | For external mail house or phone bank |
| **Save as Smart List** | Dynamic list that auto-updates as criteria match |
| **Schedule Follow-up** | Create workflow to check back in X days |

**AI Analysis Prompts (Behind the Scenes):**

The AI targeting recommendations are generated by prompts like:

```
Given:
- District sentiment by precinct (attached)
- Message volume and categories (attached)
- Voter file summary: X low-propensity, Y uncontacted (attached)
- Upcoming events: election in 47 days

Generate 3-5 actionable targeting recommendations with:
1. Specific audience criteria
2. Rationale based on data
3. Recommended action and message theme
4. Urgency/priority level
```

**Technical Implementation:**

| Component | Technology |
|-----------|------------|
| Map rendering | Mapbox GL JS or Leaflet with vector tiles |
| Geocoding | Census Geocoder API (free) or Smarty (paid) |
| Geographic boundaries | Census TIGER/Line shapefiles (free) |
| Heat map aggregation | PostGIS for spatial queries |
| AI recommendations | Claude/OpenAI with structured output |
| Real-time updates | WebSocket for live dashboard refresh |

**Data Requirements:**

| Data | Source | Update Frequency |
|------|--------|------------------|
| Voter file | L2/TargetSmart | Monthly |
| District boundaries | Census | Yearly |
| Precinct boundaries | State/county election offices | Per redistricting |
| Constituent addresses | Contact records | Real-time |
| Sentiment/issues | Dewey AI analysis | Real-time |

**Privacy & Compliance:**

- All voter data is public record, but display responsibly
- Aggregate views by default, individual data requires permission level
- Audit log all targeting queries and exports
- GOTV activities must comply with election laws (no targeting by race, etc.)
- Clear data retention policies

**This feature alone could justify switching from IQ** - it transforms Dewey from a message management tool into a constituent intelligence platform.

---

## Competitive Positioning Strategy

### Differentiation Message

> **"Dewey is the AI-powered constituent management platform that does in seconds what takes your staff hours."**

Key differentiators to emphasize:
1. **AI Analysis** - Automatic tone detection, categorization, and response suggestions
2. **Campaign Detection** - Instantly identify coordinated messaging campaigns
3. **Modern UX** - Intuitive interface, not 20-year-old technology
4. **Developer-Friendly** - Full API, webhooks, BI integration
5. **Responsive Development** - Address IQ's reputation for ignoring user feedback

### Target Early Adopters

1. **Freshman Congress members** - Not locked into IQ contracts
2. **State/local governments** - Less rigorous procurement, faster decisions
3. **Government agencies** - Less legislative focus, more service-oriented
4. **Private sector** - Companies needing constituent/customer feedback management

### Pricing Strategy

Given IQ's $1,860+/month pricing:
- **Entry tier**: $999/month (undercut significantly)
- **Pro tier**: $1,499/month (feature parity)
- **Enterprise tier**: $1,999/month (AI premium)

---

## Implementation Roadmap

### Phase 1: Foundation (Q1)
- ✅ Core CRM (contacts, messages, categories)
- ✅ AI analysis (tone, entities, categorization)
- ✅ Form builder with pre-identified links
- ✅ Email templates and campaigns
- ✅ Workflow automation
- ⏳ Basic analytics dashboard

### Phase 2: Government Essentials (Q2)
- [ ] Casework/Services module
- [ ] Physical mail entry interface
- [ ] District/geographic lookup (Census geocoding, district APIs)
- [ ] Voter file integration (L2 or TargetSmart API)
- [ ] Staff productivity reporting
- [ ] Document library

### Phase 3: Legislative (Q3)
- [ ] Bill tracking integration (Congress.gov API)
- [ ] Vote record management
- [ ] Position tracking
- [ ] Bill-message linking
- [ ] Legislative analytics

### Phase 4: Communication Channels (Q4)
- [ ] Social media integration (start with Twitter/X)
- [ ] SMS/texting capability
- [ ] Events/calendar module
- [ ] Fax integration

### Phase 5: Geographic Intelligence & AI Targeting (Q4-Q5)
- [ ] Geographic heat map visualization (Mapbox/Leaflet + PostGIS)
- [ ] Multi-layer map views (sentiment, voter propensity, issues, party)
- [ ] Drill-down hierarchy (district → precinct → block → address)
- [ ] AI-powered targeting recommendations engine
- [ ] Targeting criteria builder (voter history + sentiment + geography + issues)
- [ ] Campaign actions integration (mail merge, email, SMS, form links)
- [ ] Smart lists (dynamic segments that auto-update)

### Phase 6: Compliance (Ongoing)
- [ ] FedRAMP authorization process
- [ ] SOC 2 Type II certification
- [ ] FISMA compliance documentation

---

## Conclusion

Dewey has significant AI/automation advantages that IQ cannot easily replicate given its legacy architecture. However, Dewey lacks several **table-stakes features** for the government market:

**Must-have for market entry:**
1. Legislative module
2. Casework/services
3. FedRAMP authorization

**Must-have for competitive parity:**
4. Social media integration
5. Events/calendar
6. SMS capability

**Potential "killer feature" differentiator:**
7. **Geographic Intelligence Dashboard with AI-Powered Targeting** - This capability (heat maps, voter propensity visualization, AI-generated targeting recommendations, integrated campaign actions) does not exist in IQ and would represent a genuine leap beyond what any current constituent CRM offers. It transforms Dewey from a message management tool into a **constituent intelligence platform**.

The recommended strategy is to pursue **state/local government and private sector** initially while building out legislative/casework features and pursuing FedRAMP, then attack the Congressional market with a compelling AI differentiation story centered on the Geographic Intelligence capabilities.

---

## Sources

- [Leidos IQ CRM](https://leidosiq.com/iq-crm/)
- [IQ Help Documentation](https://iq-help.intranetquorum.com/IQ4.1/Help/topics/idh-topic130.htm)
- [IQ Social Media Integration](https://intranetquorum.com/iq-social-media-integration)
- [G2 Reviews - IQ CRM](https://www.g2.com/products/iq-crm/reviews)
- [G2 Reviews - Intranet Quorum](https://www.g2.com/products/intranet-quorum/reviews)
- [SourceForge - Intranet Quorum Reviews](https://sourceforge.net/software/product/Intranet-Quorum/)
- [Slashdot - Intranet Quorum](https://slashdot.org/software/p/Intranet-Quorum/)
- [FedRAMP Authorization Announcement](https://www.prnewswire.com/news-releases/leidos-crm-iq-fedcloud-authorized-by-fedramp-300891386.html)
- [PoliScribe (Complementary Tool)](https://poliscribe.com/congress)
