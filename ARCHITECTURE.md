# 🏗 VibeJobHunter - Architecture

System design and technical architecture.

---

## 📐 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
├──────────────────┬──────────────────┬───────────────────┤
│   CLI Commands   │  Web Dashboard   │   API Endpoints   │
└────────┬─────────┴────────┬─────────┴──────────┬────────┘
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   Core Application    │
                │  - ProfileManager     │
                │  - ApplicationManager │
                └───────────┬───────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐
    │  AI     │      │  Scrapers │     │   Data    │
    │ Agents  │      │           │     │  Storage  │
    └─────────┘      └───────────┘     └───────────┘
         │                  │                  │
    ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐
    │ Claude  │      │ LinkedIn  │     │   JSON    │
    │ OpenAI  │      │  Indeed   │     │   Files   │
    └─────────┘      └───────────┘     └───────────┘
```

---

## 🧩 Component Architecture

### 1. Core Layer (`src/core/`)

**Responsibilities**: Configuration, models, and core business logic

**Components**:
- `config.py` - Application settings and configuration
- `models.py` - Data models (Profile, JobPosting, Application, etc.)
- `profile_manager.py` - Profile management and resume parsing

**Key Features**:
- Pydantic models for type safety
- Environment-based configuration
- JSON serialization/deserialization
- Profile persistence

### 2. Agent Layer (`src/agents/`)

**Responsibilities**: AI-powered intelligence and decision making

**Components**:
- `job_matcher.py` - Job scoring and matching algorithm
- `content_generator.py` - Resume and cover letter generation
- `application_manager.py` - Application tracking and management

**Key Features**:
- Claude AI integration for intelligent analysis
- Context-aware content generation
- Match score calculation (0-100)
- Timeline tracking

### 3. Scraper Layer (`src/scrapers/`)

**Responsibilities**: Job discovery and data extraction

**Components**:
- `base_scraper.py` - Abstract base class
- `linkedin_scraper.py` - LinkedIn job scraping
- `indeed_scraper.py` - Indeed job scraping

**Key Features**:
- Async job fetching
- Rate limiting
- Error handling
- Standardized job data format

### 4. API Layer (`src/api/`)

**Responsibilities**: Web interface and REST API

**Components**:
- `app.py` - FastAPI application

**Key Features**:
- RESTful endpoints
- Web dashboard UI
- Real-time statistics
- CORS support

### 5. CLI Layer (`src/main.py`)

**Responsibilities**: Command-line interface

**Features**:
- Click-based commands
- Rich console output
- Interactive prompts
- Progress indicators

---

## 🔄 Data Flow

### Job Search Flow

```
User Command
    │
    ├─> Search Parameters
    │       │
    │       ├─> LinkedIn Scraper ──┐
    │       ├─> Indeed Scraper ────┤
    │       └─> [More sources]     │
    │                              │
    │   <── Raw Job Listings ──────┘
    │           │
    │           ├─> Job Matcher (AI Analysis)
    │           │       │
    │           │       ├─> Calculate Match Score
    │           │       ├─> Generate Match Reasons
    │           │       └─> Filter by Criteria
    │           │
    │   <── Scored Jobs
    │           │
    │           └─> Save to data/jobs/
    │
    └─> Display Results
```

### Application Flow

```
User Applies
    │
    ├─> Select Job
    │       │
    │       ├─> Content Generator
    │       │       │
    │       │       ├─> Tailor Resume (AI)
    │       │       ├─> Write Cover Letter (AI)
    │       │       └─> Generate LinkedIn Message
    │       │
    │   <── Generated Content
    │           │
    │           ├─> Save Files
    │           │   - tailored_resumes/
    │           │   - cover_letters/
    │           │
    │           └─> Create Application Record
    │                   │
    │                   ├─> Set Status: APPLIED
    │                   ├─> Add to Timeline
    │                   └─> Save to data/applications/
    │
    └─> Display Confirmation
```

### Status Update Flow

```
Status Change
    │
    ├─> Update Application
    │       │
    │       ├─> Change Status
    │       ├─> Add Timeline Event
    │       ├─> Update Timestamps
    │       └─> Schedule Follow-up (if needed)
    │
    ├─> Save Application
    │
    └─> Update Statistics
```

---

## 💾 Data Architecture

### Storage Strategy: Local-First JSON

**Why JSON?**
- Human-readable
- Easy to backup
- No database setup
- Version control friendly
- Portable across systems

### Directory Structure

```
data/
├── profiles/
│   └── profile.json                    # User profile
│
├── jobs/
│   ├── abc123def456.json               # Job posting 1
│   ├── xyz789ghi012.json               # Job posting 2
│   └── ...                             # More jobs
│
├── applications/
│   ├── abc123def456.json               # Application 1
│   ├── xyz789ghi012.json               # Application 2
│   └── ...                             # More applications
│
└── stats/
    ├── 2025-01-15.json                 # Daily stats
    ├── 2025-01-16.json
    └── ...
```

### Data Models

**Profile Schema**:
```json
{
  "name": "string",
  "email": "string",
  "location": "string",
  "skills": ["skill1", "skill2"],
  "experience_years": 10,
  "key_achievements": ["achievement1"],
  "target_roles": ["role1", "role2"],
  "resume_text": "full resume text",
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T10:00:00"
}
```

**JobPosting Schema**:
```json
{
  "id": "abc123",
  "title": "AI Engineer",
  "company": "StartupCo",
  "location": "Remote",
  "description": "full description",
  "requirements": ["req1", "req2"],
  "source": "linkedin",
  "url": "https://...",
  "match_score": 85.5,
  "match_reasons": ["reason1", "reason2"],
  "applied": false,
  "discovered_at": "2025-01-15T10:00:00"
}
```

**Application Schema**:
```json
{
  "id": "abc123",
  "job_id": "abc123",
  "job_title": "AI Engineer",
  "company": "StartupCo",
  "status": "applied",
  "applied_date": "2025-01-15T10:00:00",
  "timeline": [
    {
      "status": "applied",
      "timestamp": "2025-01-15T10:00:00",
      "note": "Application submitted"
    }
  ],
  "resume_version": "markdown content",
  "cover_letter_content": "letter content",
  "next_follow_up": "2025-01-22T10:00:00"
}
```

---

## 🤖 AI Integration

### Claude API Usage

**Model**: `claude-3-5-sonnet-20241022`

**Use Cases**:
1. **Resume Parsing** (4K tokens)
   - Extract structured data from PDF
   - Identify skills, experience, achievements
   
2. **Job Matching** (1K tokens per job)
   - Calculate match score
   - Generate match reasons
   - Identify aligned/missing skills
   
3. **Resume Tailoring** (4K tokens)
   - Rewrite resume for specific job
   - Emphasize relevant experience
   - Optimize for ATS
   
4. **Cover Letter Generation** (2K tokens)
   - Personalized content
   - Company-specific references
   - Professional tone
   
5. **Interview Prep** (3K tokens)
   - Company research
   - Likely questions
   - Suggested answers

**Cost Optimization**:
- Cache profile data in prompts
- Batch similar requests
- Use appropriate token limits
- Retry logic for failures

---

## 🔌 External Integrations

### Job Platforms

**LinkedIn**:
- HTTP scraping (no official API for job search)
- BeautifulSoup for HTML parsing
- Rate limiting: 1 req/sec
- User-Agent spoofing

**Indeed**:
- HTTP scraping
- Similar to LinkedIn approach
- Rate limiting: 1 req/sec

**Future Integrations**:
- AngelList API
- Y Combinator jobs
- Twitter/X API
- Company career pages

### AI Services

**Anthropic Claude**:
- Primary AI for intelligent features
- REST API via `anthropic` Python SDK
- Streaming support for long responses

**OpenAI GPT** (Optional):
- Alternative AI backend
- Fallback option
- Embeddings for similarity search

---

## 🚦 Error Handling

### Strategy

**Graceful Degradation**:
- Continue operation even if one component fails
- Fallback to simpler algorithms when AI fails
- Detailed error logging

**Retry Logic**:
- Exponential backoff for API calls
- Max 3 retries
- Skip failed jobs rather than crash

**User Feedback**:
- Clear error messages
- Suggestions for fixes
- Logs stored in `logs/`

---

## 🔐 Security

### API Key Management
- Stored in `.env` (never committed)
- Loaded via `python-dotenv`
- No hardcoded credentials

### Data Privacy
- All data stored locally
- No cloud sync (unless user configures)
- Resume data only sent to Claude API
- No third-party analytics

### Scraping Ethics
- Respect robots.txt
- Rate limiting to avoid overload
- User-Agent identification
- Public data only

---

## ⚡ Performance

### Optimization Strategies

**Async Operations**:
- Concurrent job fetching
- Parallel AI requests
- Non-blocking I/O

**Caching**:
- Profile data cached in memory
- Job data persisted to disk
- Avoid re-parsing same resume

**Rate Limiting**:
- 1 req/sec to job platforms
- 5 req/sec to Claude (within limits)
- Configurable delays

---

## 📊 Monitoring & Logging

### Logging Strategy

**Levels**:
- DEBUG: Detailed debugging info
- INFO: General progress
- WARNING: Non-critical issues
- ERROR: Critical failures

**Destinations**:
- Console: INFO and above
- Files: All levels to `logs/app.log`
- Rotation: Daily log files

### Metrics Tracked
- Jobs discovered per run
- Match score distribution
- API call latency
- Success/failure rates
- Application conversion funnel

---

## 🧪 Testing Strategy

### Test Coverage (Future)

**Unit Tests**:
- Model validation
- Scoring algorithm
- Content generation
- Data persistence

**Integration Tests**:
- Scraper functionality
- AI integration
- End-to-end workflows

**Manual Testing**:
- Resume parsing accuracy
- Cover letter quality
- UI/UX validation

---

## 🔄 Deployment

### Requirements

**System**:
- Python 3.9+
- 2GB RAM minimum
- 1GB disk space

**External**:
- Internet connection
- Anthropic API access
- (Optional) LinkedIn account

### Installation

```bash
# Clone repo
git clone <repo>

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with API keys

# Run setup
python setup.py
```

---

## 🔮 Future Architecture

### Planned Improvements

**Database**:
- SQLite for better querying
- Full-text search
- Relationship tracking

**Message Queue**:
- Celery for background jobs
- Scheduled tasks
- Async processing

**Microservices** (Optional):
- Separate scraper service
- Dedicated AI service
- API gateway

**Cloud Features** (Optional):
- Cloud sync
- Multi-device support
- Collaborative features

---

## 📚 Technology Stack

### Core
- **Python 3.9+** - Main language
- **Pydantic** - Data validation
- **Click** - CLI framework
- **Rich** - Terminal UI

### AI/ML
- **Anthropic Claude** - Primary AI
- **OpenAI GPT** - Alternative
- **LangChain** - AI orchestration

### Web
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **Jinja2** - Templates

### Data
- **JSON** - Data storage
- **PyPDF2** - PDF parsing
- **python-docx** - Word docs

### Web Scraping
- **aiohttp** - Async HTTP
- **BeautifulSoup** - HTML parsing
- **Selenium** - Browser automation

---

## 🤝 Contributing

### Code Style
- PEP 8 compliance
- Type hints everywhere
- Docstrings for all public functions
- Clear variable names

### Project Structure
- Modular design
- Separation of concerns
- Single responsibility principle
- DRY (Don't Repeat Yourself)

---

**Questions? Check README.md or open an issue!** 📖
