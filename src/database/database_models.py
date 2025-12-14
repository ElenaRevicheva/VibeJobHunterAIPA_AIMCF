"""
Database models for VibeJobHunter application tracking
Uses SQLAlchemy ORM for clean database interactions
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()


class JobListing(Base):
    """Job postings found by scrapers"""
    __tablename__ = 'job_listings'
    
    id = Column(String, primary_key=True)  # company_slug + job_id
    company = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    description = Column(Text)
    location = Column(String)
    remote_type = Column(String)  # fully_remote, remote_friendly, hybrid, on_site
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    
    # Metadata
    ats_type = Column(String)  # greenhouse, lever, workable
    found_date = Column(DateTime, default=datetime.utcnow)
    last_seen_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # AI Scoring
    match_score = Column(Float)  # 0.0 to 1.0
    keywords_matched = Column(Text)  # JSON array of matched keywords
    
    # Relationships
    applications = relationship("Application", back_populates="job")


class Application(Base):
    """Track applications sent to companies"""
    __tablename__ = 'applications'
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey('job_listings.id'), nullable=False)
    
    # Application details
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String)  # linkedin, email, company_website, referral
    application_method = Column(String)  # online_form, email, linkedin_easy_apply
    
    # Materials used
    resume_version = Column(String)
    cover_letter_hash = Column(String)
    portfolio_link = Column(String)
    
    # Outreach tracking
    linkedin_message_sent = Column(Boolean, default=False)
    linkedin_message_date = Column(DateTime)
    email_sent = Column(Boolean, default=False)
    email_sent_date = Column(DateTime)
    twitter_dm_sent = Column(Boolean, default=False)
    
    # Response tracking
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime)
    response_type = Column(String)  # interview, rejection, ghosted, interested
    response_channel = Column(String)  # email, linkedin, phone
    
    # Interview stages
    interview_count = Column(Integer, default=0)
    interview_stages = Column(Text)  # JSON array: ['phone_screen', 'technical', 'onsite']
    last_interview_date = Column(DateTime)
    next_interview_date = Column(DateTime)
    
    # Outcome
    offer_received = Column(Boolean, default=False)
    offer_date = Column(DateTime)
    offer_amount = Column(Integer)
    accepted = Column(Boolean)
    rejection_reason = Column(Text)
    
    # Learning & feedback
    actual_fit_score = Column(Float)  # User rates after interview: 0.0 to 1.0
    notes = Column(Text)
    
    # Relationships
    job = relationship("JobListing", back_populates="applications")
    follow_ups = relationship("FollowUp", back_populates="application")


class FollowUp(Base):
    """Track follow-up messages and interactions"""
    __tablename__ = 'follow_ups'
    
    id = Column(String, primary_key=True)
    application_id = Column(String, ForeignKey('applications.id'), nullable=False)
    
    follow_up_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    channel = Column(String)  # email, linkedin, phone
    message_type = Column(String)  # thank_you, status_check, additional_info
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime)
    notes = Column(Text)
    
    # Relationships
    application = relationship("Application", back_populates="follow_ups")


class Company(Base):
    """Company profiles and metadata"""
    __tablename__ = 'companies'
    
    slug = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ats_type = Column(String)
    website = Column(String)
    linkedin_url = Column(String)
    
    # Tracking
    total_applications = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    total_interviews = Column(Integer, default=0)
    response_rate = Column(Float)  # auto-calculated
    
    # Flags
    is_ghost_company = Column(Boolean, default=False)  # Never responds
    is_responsive = Column(Boolean, default=False)  # Responds quickly
    avg_response_days = Column(Float)
    
    # Last activity
    last_checked = Column(DateTime, default=datetime.utcnow)
    last_application_sent = Column(DateTime)


class LearningMetric(Base):
    """Track what works and what doesn't"""
    __tablename__ = 'learning_metrics'
    
    id = Column(String, primary_key=True)
    metric_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Weekly aggregates
    week_start = Column(DateTime, nullable=False)
    applications_sent = Column(Integer, default=0)
    responses_received = Column(Integer, default=0)
    interviews_scheduled = Column(Integer, default=0)
    offers_received = Column(Integer, default=0)
    
    # Performance
    response_rate = Column(Float)
    interview_conversion = Column(Float)
    offer_conversion = Column(Float)
    
    # Best performers
    top_keywords = Column(Text)  # JSON array
    top_companies = Column(Text)  # JSON array
    top_sources = Column(Text)  # JSON array
    
    # Insights (AI-generated)
    ai_insights = Column(Text)
    recommendations = Column(Text)


# Database setup functions
def get_engine(db_path: str = None):
    """Create database engine"""
    if db_path is None:
        db_path = os.getenv('DATABASE_URL', 'sqlite:///autonomous_data/vibejobhunter.db')
    
    engine = create_engine(db_path, echo=False)
    return engine


def init_database(db_path: str = None):
    """Initialize database with all tables"""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    """Get database session"""
    if engine is None:
        engine = get_engine()
    
    Session = sessionmaker(bind=engine)
    return Session()


# Helper functions for common queries
class DatabaseHelper:
    """Helper class for common database operations"""
    
    def __init__(self, session=None):
        self.session = session or get_session()
    
    def add_job_listing(self, job_data: dict):
        """Add or update a job listing"""
        job = self.session.query(JobListing).filter_by(id=job_data['id']).first()
        
        if job:
            # Update last_seen_date
            job.last_seen_date = datetime.utcnow()
        else:
            # Create new job
            job = JobListing(**job_data)
            self.session.add(job)
        
        self.session.commit()
        return job
    
    def record_application(self, job_id: str, application_data: dict):
        """Record a new application"""
        app = Application(job_id=job_id, **application_data)
        self.session.add(app)
        
        # Update company stats
        job = self.session.query(JobListing).filter_by(id=job_id).first()
        if job:
            company = self.session.query(Company).filter_by(slug=job.company).first()
            if company:
                company.total_applications += 1
                company.last_application_sent = datetime.utcnow()
        
        self.session.commit()
        return app
    
    def record_response(self, application_id: str, response_data: dict):
        """Record a response to an application"""
        app = self.session.query(Application).filter_by(id=application_id).first()
        if app:
            app.response_received = True
            app.response_date = datetime.utcnow()
            for key, value in response_data.items():
                setattr(app, key, value)
            
            # Update company stats
            job = app.job
            company = self.session.query(Company).filter_by(slug=job.company).first()
            if company:
                company.total_responses += 1
                company.response_rate = company.total_responses / company.total_applications
                
                # Calculate avg response time
                if app.response_date and app.applied_date:
                    days_to_respond = (app.response_date - app.applied_date).days
                    if company.avg_response_days:
                        company.avg_response_days = (company.avg_response_days + days_to_respond) / 2
                    else:
                        company.avg_response_days = days_to_respond
            
            self.session.commit()
        return app
    
    def get_weekly_stats(self, weeks_ago: int = 0):
        """Get statistics for a specific week"""
        from datetime import timedelta
        
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday() + (weeks_ago * 7))
        week_end = week_start + timedelta(days=7)
        
        applications = self.session.query(Application).filter(
            Application.applied_date >= week_start,
            Application.applied_date < week_end
        ).all()
        
        stats = {
            'week_start': week_start,
            'applications_sent': len(applications),
            'responses_received': sum(1 for a in applications if a.response_received),
            'interviews_scheduled': sum(1 for a in applications if a.interview_count > 0),
            'offers_received': sum(1 for a in applications if a.offer_received),
        }
        
        if stats['applications_sent'] > 0:
            stats['response_rate'] = stats['responses_received'] / stats['applications_sent']
        else:
            stats['response_rate'] = 0.0
        
        return stats
    
    def get_ghost_companies(self, min_applications: int = 3):
        """Get companies that never respond"""
        companies = self.session.query(Company).filter(
            Company.total_applications >= min_applications,
            Company.response_rate == 0
        ).all()
        return [c.slug for c in companies]
    
    def get_responsive_companies(self, min_response_rate: float = 0.5):
        """Get companies with high response rates"""
        companies = self.session.query(Company).filter(
            Company.response_rate >= min_response_rate,
            Company.total_applications >= 2
        ).all()
        return [(c.slug, c.response_rate) for c in companies]
    
    def close(self):
        """Close database session"""
        self.session.close()


if __name__ == '__main__':
    # Initialize database when run directly
    print(" Initializing VibeJobHunter database...")
    engine = init_database()
    print(" Database created successfully!")
    print(f" Location: {engine.url}")
    
    # Print table info
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\n Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
