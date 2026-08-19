import datetime
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .database import engine, Base, SessionLocal
from .models import (
    User, Child, Subject, ChildSubject, Unit, Lesson, LessonDay, QuizQuestion, 
    StudentProgress, LearningEvidence, ParentAlert, AIRecommendation
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception:
        return f"plain:{password}"

OFFICIAL_SUBJECTS = [
    {"title": "Mathematics", "slug": "mathematics", "icon": "📐", "color": "#38BDF8", "description": "Core numeracy, arithmetic, fractions, problem solving and algebra"},
    {"title": "English Language", "slug": "english-language", "icon": "📖", "color": "#4ADE80", "description": "Reading comprehension, grammar, composition and communication"},
    {"title": "Science", "slug": "science", "icon": "🔬", "color": "#3B82F6", "description": "Scientific exploration, biology, chemistry, physics and earth sciences"},
    {"title": "Phonics", "slug": "phonics", "icon": "🔤", "color": "#F59E0B", "description": "Letter sounds, decoding, blending and early literacy foundations"},
    {"title": "English Literature", "slug": "english-literature", "icon": "📚", "color": "#8B5CF6", "description": "Classic poetry, storytelling, thematic analysis and prose"},
    {"title": "Biology", "slug": "biology", "icon": "🧬", "color": "#10B981", "description": "Living organisms, plant biology, human anatomy and ecosystems"},
    {"title": "Chemistry", "slug": "chemistry", "icon": "🧪", "color": "#EC4899", "description": "Matter, elements, chemical reactions and molecular structures"},
    {"title": "Physics", "slug": "physics", "icon": "⚡", "color": "#6366F1", "description": "Forces, energy, light, electricity, motion and the universe"},
    {"title": "History", "slug": "history", "icon": "🏛️", "color": "#D97706", "description": "World civilizations, ancient empires, heritage and cultural narratives"},
    {"title": "Geography", "slug": "geography", "icon": "🌍", "color": "#0EA5E9", "description": "Physical landscapes, climate, mapping, continents and human geography"},
    {"title": "Critical Thinking & Logic", "slug": "critical-thinking-logic", "icon": "💡", "color": "#A855F7", "description": "Deductive reasoning, problem framing, fallacies and decision making"},
    {"title": "Understanding The Word", "slug": "understanding-the-word", "icon": "✝️", "color": "#FBBF24", "description": "Biblical wisdom, character virtues, moral foundation and scripture studies"},
]

def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # 1. Ensure all 12 official subjects exist
    subject_map = {}
    for s_info in OFFICIAL_SUBJECTS:
        subj = db.query(Subject).filter(Subject.slug == s_info["slug"]).first()
        if not subj:
            subj = Subject(
                title=s_info["title"],
                slug=s_info["slug"],
                icon=s_info["icon"],
                color=s_info["color"],
                description=s_info["description"]
            )
            db.add(subj)
            db.commit()
            db.refresh(subj)
        subject_map[subj.slug] = subj

    # 2. Ensure default demo parent & admin exist
    parent_user = db.query(User).filter(User.email == "sarah@email.com").first()
    if not parent_user:
        parent_user = User(
            email="sarah@email.com",
            name="Sarah Wilson",
            password_hash=get_password_hash("password"),
            role="parent",
            avatar="S"
        )
        db.add(parent_user)
        db.commit()
        db.refresh(parent_user)

    admin_user = db.query(User).filter(User.email == "jake@email.com").first()
    if not admin_user:
        admin_user = User(
            email="jake@email.com",
            name="Jake Admin",
            password_hash=get_password_hash("password"),
            role="admin",
            avatar="J"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

    # 3. Seed multi-day curriculum if not present
    math = subject_map["mathematics"]
    eng = subject_map["english-language"]
    sci = subject_map["science"]
    phon = subject_map["phonics"]
    hist = subject_map["history"]

    # =========================================================================
    # LEVEL 0 (Reception / Kindergarten) - Mathematics: Number Sense (Counting to 5)
    # =========================================================================
    u_math0 = db.query(Unit).filter(Unit.subject_id == math.id, Unit.level == 0, Unit.title == "Unit 1: Number Sense & Early Counting").first()
    if not u_math0:
        u_math0 = Unit(subject_id=math.id, level=0, title="Unit 1: Number Sense & Early Counting", order_num=1)
        db.add(u_math0)
        db.commit()
        db.refresh(u_math0)

    l_math0_1 = db.query(Lesson).filter(Lesson.unit_id == u_math0.id, Lesson.title == "Counting to 5").first()
    if not l_math0_1:
        l_math0_1 = Lesson(
            unit_id=u_math0.id,
            level=0,
            title="Counting to 5",
            topic="Counting to 5",
            order_num=1,
            objectives=["Count up to 5 objects accurately", "Recognize numerals 1, 2, 3, 4, 5", "Match quantity to number word"],
            learn_content="Numbers help us count God's wonderful creation! Each number represents a special quantity: 1, 2, 3, 4, 5. Let's count together!",
            examples=[{"title": "Counting Teddy Bears 🧸", "calc": "1, 2, 3, 4, 5 bears", "explanation": "Point to each bear one by one as you say the number."}],
            vocabulary=[{"word": "Count", "definition": "To name numbers in order to find total quantity."}, {"word": "Quantity", "definition": "How many of something there are."}],
            key_points=["Every object gets one number word.", "The last number you say is the total amount."],
            bible_reflection="Psalm 139:14 — 'I will praise You, for I am fearfully and wonderfully made.' God knows the exact number of hairs on our heads!",
            character_connection="Attentiveness: Paying close attention as we count each item carefully.",
            default_evidence_task="Count 5 of your favorite toys in a row, and write the numbers 1 to 5."
        )
        db.add(l_math0_1)
        db.commit()
        db.refresh(l_math0_1)

        # Day 1: Explore
        d1 = LessonDay(
            lesson_id=l_math0_1.id,
            day_number=1,
            activity_type="Explore",
            title="Counting to 5 — Day 1 (Explore)",
            learning_objectives=["Explore counting 1 to 5 with physical objects", "Touch and count objects one by one"],
            key_concept="Counting assigns one number name to each object in order.",
            bible_reference="Psalm 139:14",
            biblical_theme="God's Precision and Care",
            biblical_application="God made each of us unique and knows every detail about us.",
            character_reference="Attentiveness",
            estimated_duration="20 mins",
            ai_script="Hello! Today we are exploring counting to 5. Look around you—can you spot 5 things in your room?",
            real_world_context="Counting toys, shoes, or fruits at home",
            visual_support="Five colorful blocks lined up from 1 to 5",
            practice_questions=[{"q": "How many fingers do you have on one hand?", "options": ["3", "4", "5", "6"], "answer": "5"}],
            vocabulary=["Count", "Number", "One", "Two", "Three", "Four", "Five"],
            reading_recommendations=["Five Little Monkeys", "Ten Little Caterpillars"]
        )
        # Day 2: Practice
        d2 = LessonDay(
            lesson_id=l_math0_1.id,
            day_number=2,
            activity_type="Practice",
            title="Counting to 5 — Day 2 (Practice)",
            learning_objectives=["Match numerals 1-5 to dot cards and pictures", "Write the numerals 1 to 5"],
            key_concept="Numerals are symbols that represent specific amounts.",
            bible_reference="Proverbs 3:5",
            biblical_theme="Trust and Order",
            biblical_application="God gave us numbers so the world operates with order and beauty.",
            character_reference="Patience",
            estimated_duration="20 mins",
            ai_script="Welcome back! Today we practice writing our numbers 1, 2, 3, 4, and 5.",
            real_world_context="Writing numbers on a calendar or drawing cards",
            visual_support="Dot cards showing patterns for 1 through 5",
            practice_questions=[{"q": "Which numeral comes after 3?", "options": ["2", "4", "5", "1"], "answer": "4"}],
            vocabulary=["Numeral", "Order", "Next"],
            reading_recommendations=["Count with Me"]
        )
        # Day 3: Apply
        d3 = LessonDay(
            lesson_id=l_math0_1.id,
            day_number=3,
            activity_type="Apply",
            title="Counting to 5 — Day 3 (Apply)",
            learning_objectives=["Solve sharing problems with sets of 5 items", "Compare groups of objects up to 5"],
            key_concept="Counting helps us share fairly and solve everyday puzzles.",
            bible_reference="Galatians 6:9",
            biblical_theme="Generosity and Kindness",
            biblical_application="Using our counting skills to share snacks and toys with family.",
            character_reference="Generosity",
            estimated_duration="25 mins",
            ai_script="Today is Day 3 Apply! Let's use our counting skills to solve a sharing story.",
            real_world_context="Sharing 5 apples between friends",
            visual_support="Two baskets sharing 5 apples",
            practice_questions=[{"q": "If you have 4 apples and get 1 more, how many do you have?", "options": ["3", "4", "5", "6"], "answer": "5"}],
            vocabulary=["Total", "Share", "Equal"],
            reading_recommendations=["Sharing with Friends"]
        )
        db.add_all([d1, d2, d3])
        db.commit()

        # Quiz Questions
        db.add_all([
            QuizQuestion(lesson_id=l_math0_1.id, question="How many stars are here: ⭐ ⭐ ⭐?", options=["2", "3", "4", "5"], correct_answer="3", explanation_correct="Spot on! There are 3 stars! ⭐⭐⭐", explanation_incorrect="Count them one by one: 1, 2, 3!"),
            QuizQuestion(lesson_id=l_math0_1.id, question="Which number comes directly after 4?", options=["3", "5", "2", "6"], correct_answer="5", explanation_correct="Awesome! 5 comes right after 4! 🌟", explanation_incorrect="Let's count: 1, 2, 3, 4, 5!"),
            QuizQuestion(lesson_id=l_math0_1.id, question="How many fingers are on one hand?", options=["4", "5", "6", "3"], correct_answer="5", explanation_correct="Yay! 5 fingers on one hand! ✋", explanation_incorrect="Count your fingers on one hand: 1, 2, 3, 4, 5!"),
        ])
        db.commit()

    # =========================================================================
    # LEVEL 4 (Year 4 / Grade 4) - Mathematics: Fractions & Equivalence
    # =========================================================================
    u_math4 = db.query(Unit).filter(Unit.subject_id == math.id, Unit.level == 4, Unit.title == "Unit 1: Fractions, Decimals & Equivalence").first()
    if not u_math4:
        u_math4 = Unit(subject_id=math.id, level=4, title="Unit 1: Fractions, Decimals & Equivalence", order_num=1)
        db.add(u_math4)
        db.commit()
        db.refresh(u_math4)

    l_math4_1 = db.query(Lesson).filter(Lesson.unit_id == u_math4.id, Lesson.title == "Fractions Practice: Understanding Equivalence").first()
    if not l_math4_1:
        l_math4_1 = Lesson(
            unit_id=u_math4.id,
            level=4,
            title="Fractions Practice: Understanding Equivalence",
            topic="Equivalent Fractions",
            order_num=1,
            objectives=["Understand what an equivalent fraction represents", "Calculate equivalent fractions by multiplying numerator and denominator", "Solve sharing scenarios"],
            learn_content="Two fractions are equivalent when they represent the exact same quantity (like 1/2 and 2/4). They are the exact same size slice of pizza, just sliced into smaller pieces!",
            examples=[{"title": "Example (Half Pizza)", "calc": "1/2 = 2/4 (multiply by 2/2)", "explanation": "Multiply top and bottom by 2. The total value is identical."}],
            vocabulary=[{"word": "Numerator", "definition": "The top number."}, {"word": "Denominator", "definition": "The bottom number showing total parts."}],
            key_points=["Multiply or divide numerator and denominator by the same number.", "The overall value never changes."],
            bible_reflection="Proverbs 11:1 — 'A false balance is an abomination to the Lord, but a just weight is His delight.' Fairness in portions reflects God's justice.",
            character_connection="Fairness: Sharing portions accurately and honestly builds trust among family and friends.",
            default_evidence_task="Draw or explain two fractions that are equivalent to 3/4, and show your step-by-step arithmetic working."
        )
        db.add(l_math4_1)
        db.commit()
        db.refresh(l_math4_1)

        d1_4 = LessonDay(
            lesson_id=l_math4_1.id, day_number=1, activity_type="Explore",
            title="Fractions: Equivalence — Day 1 (Explore)",
            learning_objectives=["Explore equivalent portions with bar models", "Identify equivalent fractions on a number line"],
            key_concept="Equivalent fractions represent identical quantities despite different numbers.",
            bible_reference="Proverbs 11:1", biblical_theme="Honesty and Justice", biblical_application="Accurate measurements and fair sharing.",
            character_reference="Fairness", estimated_duration="25 mins",
            ai_script="Welcome to Day 1 Explore! Today we explore why 1/2 is the same size as 2/4.",
            real_world_context="Cutting pizza and cake into equal slices",
            visual_support="Fraction strips comparing 1/2, 2/4, 4/8"
        )
        d2_4 = LessonDay(
            lesson_id=l_math4_1.id, day_number=2, activity_type="Practice",
            title="Fractions: Equivalence — Day 2 (Practice)",
            learning_objectives=["Calculate equivalent fractions using multiplication and division", "Simplify fractions"],
            key_concept="Multiply or divide both numerator and denominator by the same non-zero number.",
            bible_reference="Proverbs 11:1", biblical_theme="Faithfulness", biblical_application="Diligent problem solving.",
            character_reference="Diligence", estimated_duration="25 mins",
            ai_script="Today on Day 2 Practice, let's calculate equivalent fractions for 3/4, 2/5, and 1/3.",
            real_world_context="Baking measurements in recipes",
            visual_support="Fraction multiplication chart"
        )
        d3_4 = LessonDay(
            lesson_id=l_math4_1.id, day_number=3, activity_type="Apply",
            title="Fractions: Equivalence — Day 3 (Apply)",
            learning_objectives=["Apply equivalent fractions to solve multi-step word problems", "Create visual fraction models"],
            key_concept="Fractions allow precise division and problem solving in science and finance.",
            bible_reference="Ecclesiastes 4:9", biblical_theme="Wisdom", biblical_application="Combining resources wisely.",
            character_reference="Cooperation", estimated_duration="30 mins",
            ai_script="Day 3 Apply! Let's solve real-world sharing word problems.",
            real_world_context="Budgeting and sharing supplies",
            visual_support="Word problem scenario diagrams"
        )
        db.add_all([d1_4, d2_4, d3_4])
        db.commit()

        db.add_all([
            QuizQuestion(lesson_id=l_math4_1.id, question="Which fraction is equivalent to 1/2?", options=["2/4", "1/3", "3/5", "2/3"], correct_answer="2/4", explanation_correct="Brilliant! 1/2 × 2/2 = 2/4. 🎉", explanation_incorrect="Multiply top and bottom by 2 to get 2/4!"),
            QuizQuestion(lesson_id=l_math4_1.id, question="What does the denominator represent?", options=["Total equal parts", "Parts chosen", "Fraction sum", "Multiplier"], correct_answer="Total equal parts", explanation_correct="Spot on! Total parts in the whole. 🌟", explanation_incorrect="Denominator is the bottom number showing total parts."),
            QuizQuestion(lesson_id=l_math4_1.id, question="Which fraction is equivalent to 3/4?", options=["6/8", "4/6", "5/8", "2/3"], correct_answer="6/8", explanation_correct="Perfect! 3/4 × 2/2 = 6/8. 🏆", explanation_incorrect="Multiply top and bottom by 2 to get 6/8!"),
        ])
        db.commit()

    # 4. Seed demo children for Sarah Wilson if none exist
    if db.query(Child).filter(Child.parent_id == parent_user.id).count() == 0:
        # Leo: UK Reception (Level 0)
        leo = Child(
            parent_id=parent_user.id,
            name="Leo",
            age=5,
            education_system="UK",
            level=0,
            grade="Reception",
            avatar="🦊",
            xp=60,
            streak_days=2,
            active=True
        )
        # Mayowa: UK Year 4 (Level 4)
        mayowa = Child(
            parent_id=parent_user.id,
            name="Mayowa",
            age=9,
            education_system="UK",
            level=4,
            grade="Year 4",
            avatar="🦁",
            xp=180,
            streak_days=5,
            active=True
        )
        # Johnson: UK Year 3 (Level 3)
        johnson = Child(
            parent_id=parent_user.id,
            name="Johnson",
            age=8,
            education_system="UK",
            level=3,
            grade="Year 3",
            avatar="🐼",
            xp=95,
            streak_days=3,
            active=True
        )
        db.add_all([leo, mayowa, johnson])
        db.commit()
        db.refresh(leo)
        db.refresh(mayowa)
        db.refresh(johnson)

        # Enroll Leo in Mathematics, Science, Phonics
        for s_slug in ["mathematics", "science", "phonics"]:
            s = subject_map.get(s_slug)
            if s:
                db.add(ChildSubject(child_id=leo.id, subject_id=s.id))

        # Enroll Mayowa in Mathematics, English Language, Science
        for s_slug in ["mathematics", "english-language", "science"]:
            s = subject_map.get(s_slug)
            if s:
                db.add(ChildSubject(child_id=mayowa.id, subject_id=s.id))

        # Enroll Johnson in Mathematics, History, Science
        for s_slug in ["mathematics", "history", "science"]:
            s = subject_map.get(s_slug)
            if s:
                db.add(ChildSubject(child_id=johnson.id, subject_id=s.id))
        db.commit()

        # Seed sample evidence & alerts
        db.add(LearningEvidence(
            child_id=mayowa.id,
            lesson_id=l_math4_1.id,
            day_number=1,
            subject="Mathematics",
            lesson_title="Fractions Practice",
            skill="Equivalent fractions",
            evidence_type="lesson",
            submission_type="text",
            content="3/4 is equivalent to 6/8 because 3*2=6 and 4*2=8.",
            score=95,
            ai_feedback="Superb reasoning, Mayowa! You multiplied both numerator and denominator accurately.",
            verified=True
        ))

        db.add_all([
            ParentAlert(
                parent_id=parent_user.id,
                child_id=leo.id,
                severity="normal",
                title="Lesson Ready",
                subtitle="Leo is ready to begin Counting to 5 (Day 1 — Explore)."
            ),
            ParentAlert(
                parent_id=parent_user.id,
                child_id=mayowa.id,
                severity="normal",
                title="Evidence Verified",
                subtitle="Mayowa completed Fractions Practice with 95% score."
            ),
            AIRecommendation(
                parent_id=parent_user.id,
                child_id=mayowa.id,
                title="Add 10 min daily reading challenge",
                description="Mayowa is demonstrating great progress in English; an extra 10 min daily reading challenge will strengthen vocabulary.",
                status="pending"
            )
        ])
        db.commit()

    db.close()
    print("Curriculum & Demo Seed Data Complete!")

if __name__ == "__main__":
    seed()
