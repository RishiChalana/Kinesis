**FINAL YEAR PROJECT --- 10-PHASE DEVELOPMENT ROADMAP**

**KINESIS**

Kinematic Intelligence for Neuromuscular Exercise and Session Insight

Biomechanically-Personalised Form Analysis • Compensatory Movement
Detection

Bilateral Asymmetry Scoring • Tempo Analysis • Movement Signature
Fingerprinting

2-Person Team \| 5 Months (20 Weeks) \| 10 Phases

**What KINESIS Is**

KINESIS is not a rep counter with a dashboard. It is a
biomechanics-aware fitness intelligence platform that does things no
existing student project or GitHub repository does together in one
system: it calibrates its form thresholds to each user\'s individual
body proportions, detects compensatory movement patterns indicating
which muscle is fatiguing, tracks bilateral asymmetry as an injury risk
signal, measures exercise tempo against evidence-based targets, and
builds a personal movement signature per user per exercise that is
compared against itself --- not against a generic population standard.

Every design choice in this document is motivated by a specific gap in
existing tools. When interviewers ask why you built it this way, you
have a biomechanical or engineering answer for every decision.

**The 5 Core Innovations --- What Makes This Unreplicable**

-   **Personalised Biomechanical Calibration:** Your form thresholds are
    computed from your own measured body proportions, not population
    averages. A person with long femurs has a physically different
    optimal squat angle than someone with short femurs. Every existing
    project ignores this. KINESIS corrects it.

-   **Compensatory Movement Detection:** When a primary muscle fatigues,
    the body recruits secondary muscles. This creates correlated
    multi-joint deviations that only appear when you track 3+ joints
    simultaneously across time. KINESIS detects the pattern, not just an
    isolated angle. No student project does this.

-   **Bilateral Asymmetry Scoring:** Left-vs-right joint angle asymmetry
    above 10-15% is a clinically documented injury risk marker. KINESIS
    computes it per rep, tracks it across sessions, and alerts when a
    consistent imbalance develops. Force-plate equivalent from a webcam.

-   **Exercise Tempo Analysis:** The time spent in eccentric, isometric,
    and concentric phases determines muscle stimulus and injury risk. No
    existing fitness AI measures this. KINESIS timestamps every phase
    and scores against evidence-based tempo targets.

-   **Movement Signature Fingerprinting:** After enough sessions,
    KINESIS builds a statistical model of how YOU personally move
    through each exercise. New reps are compared to YOUR baseline using
    Dynamic Time Warping --- not to a generic human. This is clinical
    gait analysis applied to strength training.

**Tech Stack**

  ---------------------- --------------------- ------------------------------
  **Area**               **Technology**        **Purpose**

  **Pose Estimation**    MediaPipe Pose        33-landmark body skeleton at
                         (Python)              30fps on CPU only

  **Angle & Vector       NumPy + SciPy         Joint angles, bilateral
  Math**                                       comparison, DTW, polyfit

  **Time-series          TimescaleDB           Store landmark trajectories as
  storage**              (PostgreSQL ext)      time-series not flat rows

  **Signature matching** fastdtw (Python       Dynamic Time Warping for
                         library)              movement fingerprint
                                               comparison

  **Video / Webcam**     OpenCV                Frame capture, annotation
                                               drawing, resize, flip

  **Backend**            FastAPI + Uvicorn     REST APIs, WebSocket server,
                                               auth, session management

  **Authentication**     JWT (python-jose)     Per-user login,
                                               token-protected endpoints

  **ORM**                SQLAlchemy            Python ORM for database models
                                               and queries

  **Migrations**         Alembic               Schema versioning --- safe to
                                               evolve database

  **Frontend**           React + Vite          Webcam UI, skeleton canvas
                                               overlay, dashboard

  **Canvas overlay**     HTML5 Canvas API      Draw skeleton, asymmetry
                                               lines, compensation alerts

  **Real-time stream**   WebSockets            Push processed frame data from
                                               backend to React

  **Charts**             Recharts              Form score trends, asymmetry
                                               history, tempo graphs

  **Containerisation**   Docker + Compose      Package entire app for
                                               deployment

  **Deployment**         Render / Vercel       Backend on Render, frontend on
                                               Vercel --- both free tier
  ---------------------- --------------------- ------------------------------

**Team Roles --- Fixed for All 10 Phases**

+-----------------------------------+-----------------------------------+
| **Person A --- CV & AI Engineer** | **Person B --- Backend & Frontend |
|                                   | Engineer**                        |
+-----------------------------------+-----------------------------------+
| **MediaPipe pipeline**            | **FastAPI backend**               |
|                                   |                                   |
| Landmark extraction, visibility   | All REST endpoints, request       |
| filtering, coordinate             | models, CORS, error handling      |
| normalisation                     |                                   |
|                                   | **JWT auth**                      |
| **Angle engine**                  |                                   |
|                                   | User registration, login, token   |
| Joint angle calculation for every | verification, protected routes    |
| exercise and every check          |                                   |
|                                   | **TimescaleDB schema**            |
| **Calibration system**            |                                   |
|                                   | Hypertable design for landmark    |
| Body proportion measurement and   | time-series, indexes              |
| personalised threshold            |                                   |
| computation                       | **WebSocket server**              |
|                                   |                                   |
| **Rep state machine**             | Frame streaming,                  |
|                                   | ConnectionManager, reconnection   |
| Hysteresis-based rep counting per |                                   |
| exercise                          | **Session APIs**                  |
|                                   |                                   |
| **Compensation detector**         | Start/end workout, save reps,     |
|                                   | retrieve history                  |
| Multi-joint temporal correlation  |                                   |
| engine --- the core innovation    | **React webcam UI**               |
|                                   |                                   |
| **Bilateral asymmetry**           | getUserMedia, Canvas skeleton     |
|                                   | drawing, live alerts              |
| Left-right difference scoring per |                                   |
| rep and per session               | **Dashboard**                     |
|                                   |                                   |
| **Tempo analyser**                | Form score trends, asymmetry      |
|                                   | chart, tempo chart, error log     |
| Eccentric / isometric /           |                                   |
| concentric phase timing           | **Corrective engine**             |
|                                   |                                   |
| **Movement signature**            | Knowledge-base lookup --- error → |
|                                   | cause → corrective exercises      |
| DTW-based fingerprint model and   |                                   |
| deviation scoring                 | **Docker setup**                  |
|                                   |                                   |
| **Fatigue detector**              | Dockerfile for backend and        |
|                                   | frontend, docker-compose.yml      |
| Linear regression on rep-wise     |                                   |
| form scores within a set          | **Deployment**                    |
|                                   |                                   |
| **Injury risk engine**            | Cloud hosting, environment        |
|                                   | variables, final live URL         |
| Longitudinal pattern analysis     |                                   |
| across sessions                   |                                   |
+-----------------------------------+-----------------------------------+

+-----------------------------------------------------------------------+
| **PHASE 1: PROJECT SETUP & ENVIRONMENT**                              |
|                                                                       |
| Duration: Week 1--2 (Days 1--14) \| Both people --- foundation before |
| any code                                                              |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

No ML code. No pose detection. This phase is entirely about setting up
your machines so both people can code, run, and push without friction.
Poor setup costs weeks of debugging later. Every minute spent here saves
an hour in Phase 5.

**GOALS BY END OF PHASE**

-   Python 3.10+, Node.js 18+, Git installed and configured on both
    machines

-   Shared private GitHub repository created with agreed folder
    structure committed

-   Python virtual environment working with initial packages installed

-   FastAPI server running on localhost:8000 returning a hello-world
    response

-   React app (Vite) running on localhost:5173 showing a basic page

-   Both people have pushed and pulled at least 3 times each without
    errors

-   PostgreSQL installed locally and TimescaleDB extension installed

+-----------------------------------+-----------------------------------+
| **Person A Tasks**                | **Person B Tasks**                |
+-----------------------------------+-----------------------------------+
| **Install Python 3.10+ and pip**  | **Install Node.js 18+ and npm**   |
|                                   |                                   |
| Download from python.org. Verify: | Download from nodejs.org. Verify: |
| python \--version. Install pip if | node \--version and npm           |
| not included. Install VS Code     | \--version. Install VS Code with  |
| with the Python extension.        | ES7 React extension.              |
|                                   |                                   |
| **Git setup**                     | **Install PostgreSQL +            |
|                                   | TimescaleDB**                     |
| git config \--global user.name    |                                   |
| and user.email. Create GitHub     | PostgreSQL 15 from                |
| account if needed. Create the     | postgresql.org. After install:    |
| shared repo. Clone it. Practice:  | CREATE EXTENSION IF NOT EXISTS    |
| add, commit, push, pull, creating | timescaledb CASCADE; in psql.     |
| a branch.                         | Verify with \\dx.                 |
|                                   |                                   |
| **Virtual environment**           | **Backend dependencies**          |
|                                   |                                   |
| python -m venv venv in the        | pip install fastapi uvicorn       |
| project root. Activate it. pip    | sqlalchemy psycopg2-binary        |
| install opencv-python mediapipe   | alembic python-dotenv             |
| numpy scipy fastdtw. pip freeze   | python-jose\[cryptography\]       |
| \> requirements.txt and commit    | passlib\[bcrypt\]. Add to         |
| it.                               | requirements.txt.                 |
|                                   |                                   |
| **Test OpenCV + MediaPipe**       | **Hello-world FastAPI**           |
|                                   |                                   |
| Write a 5-line script: import cv2 | Create backend/main.py. from      |
| and mediapipe. Open webcam with   | fastapi import FastAPI. app =     |
| cv2.VideoCapture(0). Print one    | FastAPI(). \@app.get(\'/\')       |
| frame shape. Confirm no errors.   | return message. Run: uvicorn      |
| This validates your environment.  | backend.main:app \--reload. Open  |
|                                   | localhost:8000/docs.              |
| **Folder structure**              |                                   |
|                                   | **Hello-world React**             |
| Create /ml, /backend, /frontend,  |                                   |
| /docs, /data folders. Add a       | In /frontend: npm create          |
| .gitignore that excludes venv/,   | vite@latest . \-- \--template     |
| \_\_pycache\_\_/, .env,           | react. npm install. npm run dev.  |
| node_modules/. Commit and push.   | Confirm it loads in browser.      |
|                                   | Change the title to KINESIS.      |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ --------------------------
  **Topic**         **What to Study**              **Where to Study**

  **Git & GitHub**  Concepts: repository, commit,  YouTube: \'Git and GitHub
                    branch, merge, pull request,   for Beginners\' by
                    .gitignore. Commands: init,    freeCodeCamp (1 hr).
                    add, commit, push, pull,       Practice on
                    clone, checkout -b, merge. How learngitbranching.js.org
                    to resolve a simple merge      
                    conflict.                      

  **Terminal /      Navigation: cd, ls (Mac/Linux) Any beginner terminal
  Command Line**    or dir (Windows), mkdir, pwd.  tutorial for your OS.
                    Running scripts: python        Spend 1 hour practicing
                    file.py, pip install, npm run  only.
                    dev. Understanding relative vs 
                    absolute paths.                

  **Virtual         What venv is and why it exists Python official docs: venv
  Environments**    (project isolation). How to    section. 15-minute read.
                    create, activate, deactivate.  
                    Installing packages inside it. 
                    What requirements.txt is and   
                    why it matters for your        
                    teammate.                      

  **PostgreSQL      What a relational database is. PostgreSQL tutorial:
  basics**          How to start the PostgreSQL    postgresqltutorial.com ---
                    server. psql command line      first 3 sections only
                    basics: \\l (list databases),  
                    \\c (connect), \\dt (list      
                    tables), \\dx (list            
                    extensions). CREATE DATABASE   
                    command.                       

  **VS Code setup** Installing extensions. Opening VS Code official
                    integrated terminal. Setting   getting-started docs.
                    Python interpreter (bottom     30-minute setup.
                    left). GitLens extension for   
                    seeing who changed what.       
                    Keyboard shortcuts:            
                    Ctrl+Shift+P, Ctrl+\`.         
  ----------------- ------------------------------ --------------------------

+-----------------------------------------------------------------------+
| **PHASE 2: OPENCV WEBCAM & FASTAPI FOUNDATIONS**                      |
|                                                                       |
| Duration: Week 3--4 (Days 15--28) \| Person A: webcam pipeline.       |
| Person B: FastAPI + database models.                                  |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

Person A learns to work with live video in Python --- reading frames
from a webcam, displaying them, drawing on them. This is the literal
foundation that every later phase builds on. Person B learns FastAPI
properly and designs the database schema --- the structure of how all
data will be stored. By end of phase Person A has a live annotated
webcam feed. Person B has a working multi-endpoint API and all database
tables created.

**GOALS BY END OF PHASE**

-   Person A: Webcam feed open in a Python window with text and
    rectangles drawn on it

-   Person A: Understands what a frame is (a numpy array), what BGR
    means, how to flip and resize

-   Person B: FastAPI app with 6+ endpoints using path params, query
    params, and Pydantic models

-   Person B: All 6 database tables created in PostgreSQL via
    SQLAlchemy + Alembic

-   Person B: API docs at localhost:8000/docs showing all endpoints ---
    tested with Swagger UI

+-----------------------------------+-----------------------------------+
| **Person A --- OpenCV Webcam**    | **Person B --- FastAPI +          |
|                                   | Database**                        |
+-----------------------------------+-----------------------------------+
| **Open and read webcam**          | **Learn FastAPI routing**         |
|                                   |                                   |
| cap = cv2.VideoCapture(0). while  | Understand decorators: \@app.get, |
| True: ret, frame = cap.read(). if | \@app.post, \@app.patch,          |
| not ret: break.                   | \@app.delete. Path params:        |
| cv2.imshow(\'feed\', frame). if   | /users/{user_id}. Query params:   |
| cv2.waitKey(1) & 0xFF ==          | /sessions?limit=10. Run server    |
| ord(\'q\'): break. cap.release(). | and test each in Swagger UI at    |
| cv2.destroyAllWindows(). This     | /docs.                            |
| loop is the skeleton of all       |                                   |
| future code.                      | **Pydantic request models**       |
|                                   |                                   |
| **Understand the frame**          | Create models: UserCreate (name,  |
|                                   | email, password), SessionStart    |
| Print frame.shape after           | (exercise, target_sets,           |
| cap.read(). You will see (480,    | reps_per_set), RepRecord          |
| 640, 3) --- height, width, 3      | (set_num, rep_num, form_score,    |
| colour channels (BGR). Each pixel | duration_seconds). Use as request |
| is \[Blue, Green, Red\] NOT       | body type in POST endpoints.      |
| \[R,G,B\]. This order matters     |                                   |
| when you pick colours for         | **Design database schema**        |
| drawing.                          |                                   |
|                                   | 6 tables: users (id, name, email, |
| **Draw on frames**                | hashed_password, created_at),     |
|                                   | user_profiles (id, user_id,       |
| cv2.rectangle(frame, (x1,y1),     | torso_ratio, femur_ratio,         |
| (x2,y2), (0,255,0), 2) --- green  | shoulder_width_px,                |
| box, 2px thick.                   | calibrated_at), workouts (id,     |
| cv2.putText(frame, \'text\',      | user_id, exercise, started_at,    |
| (x,y), cv2.FONT_HERSHEY_SIMPLEX,  | ended_at), sets (id, workout_id,  |
| 1, (255,255,255), 2) --- white    | set_number, avg_form_score), reps |
| text. cv2.circle(frame, (cx,cy),  | (id, set_id, rep_number,          |
| radius, colour, thickness).       | form_score, tempo_eccentric_s,    |
| Practice drawing all three.       | tempo_concentric_s,               |
|                                   | left_asymmetry, right_asymmetry,  |
| **Flip and resize**               | compensation_detected),           |
|                                   | form_errors (id, rep_id,          |
| cv2.flip(frame, 1) mirrors        | error_code, severity,             |
| horizontally --- essential so     | frame_count, frames_total).       |
| user sees themselves as in a      |                                   |
| mirror, not reversed.             | **SQLAlchemy models**             |
| cv2.resize(frame, (640,480))      |                                   |
| standardises frame size for       | Create backend/models.py with all |
| consistent landmark coordinates.  | 6 classes. Each is a Python class |
|                                   | inheriting from Base. Columns use |
| **FPS counter**                   | Column(Integer), Column(String),  |
|                                   | Column(Float), Column(DateTime).  |
| import time. Track time between   | ForeignKey links child to parent. |
| frames. fps = 1 / (current_time - | Add relationship() for easy       |
| prev_time). Draw fps on frame     | cross-table access.               |
| with putText. Target: above 25    |                                   |
| FPS at this stage with no ML yet. | **Alembic migration**             |
|                                   |                                   |
|                                   | alembic init alembic. Edit        |
|                                   | alembic.ini sqlalchemy.url to     |
|                                   | point to your local PostgreSQL.   |
|                                   | Edit alembic/env.py to import     |
|                                   | your Base. alembic revision       |
|                                   | \--autogenerate -m \'initial      |
|                                   | schema\'. alembic upgrade head.   |
|                                   | Verify tables exist in psql with  |
|                                   | \\dt.                             |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ -----------------------
  **Topic**         **What to Study**              **Where to Study**

  **OpenCV video    cv2.VideoCapture, cap.read(),  YouTube: \'OpenCV
  basics (A)**      cap.release(), cv2.imshow(),   Python Tutorial for
                    cv2.waitKey(1),                Beginners\' by
                    cv2.destroyAllWindows().       freeCodeCamp --- first
                    Drawing: rectangle, putText,   40 minutes only
                    circle, line. What return code 
                    of waitKey means.              

  **NumPy array     What ndarray is. array.shape,  numpy.org quickstart
  fundamentals      array.dtype (uint8 for         tutorial --- arrays
  (A)**             images). Array slicing         section. 1-hour read.
                    img\[y1:y2, x1:x2\] crops a    
                    region. Why images are         
                    height×width×3 not             
                    width×height. np.zeros and     
                    np.ones for blank frames.      

  **BGR colour      Why OpenCV uses BGR not RGB.   OpenCV docs: colour
  model (A)**       How to specify colours as      spaces section
                    (B,G,R) tuples:                
                    green=(0,255,0),               
                    red=(0,0,255), blue=(255,0,0), 
                    white=(255,255,255).           
                    cv2.cvtColor for converting    
                    between colour spaces.         

  **FastAPI full    Path parameters, query         fastapi.tiangolo.com
  tutorial (B)**    parameters, request body,      --- official tutorial,
                    Pydantic models, response      first 10 sections. This
                    models, status codes,          is the most important
                    HTTPException, automatic /docs reading for Person B
                    generation. Read ALL of the    this phase.
                    official tutorial first steps  
                    through handling errors.       

  **SQLAlchemy ORM  What an ORM is and why it      SQLAlchemy 2.0 ORM
  (B)**             exists. DeclarativeBase,       tutorial on
                    Column, ForeignKey,            docs.sqlalchemy.org ---
                    relationship, backref.         unified tutorial
                    Session, add, commit, query.   section
                    The difference between         
                    ORM-style and core-style       
                    SQLAlchemy.                    

  **Alembic         What migrations are and why    Alembic docs:
  migrations (B)**  you need them. alembic init,   tutorial.rst --- read
                    env.py configuration, revision the full tutorial (30
                    \--autogenerate, upgrade head, min)
                    downgrade. How it tracks       
                    schema version history in the  
                    alembic_version table.         
  ----------------- ------------------------------ -----------------------

+-----------------------------------------------------------------------+
| **PHASE 3: MEDIAPIPE POSE ESTIMATION --- LANDMARKS & SKELETON**       |
|                                                                       |
| Duration: Week 5--6 (Days 29--42) \| Person A: full skeleton          |
| pipeline. Person B: JWT auth system.                                  |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

MediaPipe Pose detects 33 landmarks on the human body in every frame ---
joints from nose to ankles. Person A integrates it into the webcam
pipeline and learns which landmark ID maps to which body part. This
knowledge is used in every subsequent phase. Person B builds JWT
authentication so the system knows which user is doing which workout,
and all subsequent endpoints become protected.

**The 33 Landmarks You Must Know --- Full Reference**

**Key Landmark IDs for KINESIS**

-   **11, 12:** Left shoulder, Right shoulder --- used for torso width,
    shoulder alignment, torso lean

-   **13, 14:** Left elbow, Right elbow --- bicep curl rep counter,
    elbow flare, compensation in curls

-   **15, 16:** Left wrist, Right wrist --- bar path in deadlift, wrist
    position in push-ups

-   **17, 18:** Left pinky, Right pinky --- optional: wrist rotation
    check in bicep curl

-   **19, 20:** Left index, Right index --- fine grip position checks

-   **23, 24:** Left hip, Right hip --- squat depth, deadlift lockout,
    torso angle, BILATERAL ASYMMETRY baseline

-   **25, 26:** Left knee, Right knee --- primary squat rep counter,
    BILATERAL ASYMMETRY check, knee cave

-   **27, 28:** Left ankle, Right ankle --- heel rise check, push-up
    plank line

-   **29--32:** Foot landmarks --- heel and toe, used for toe position
    and heel rise detection

+-----------------------------------+-----------------------------------+
| **Person A --- MediaPipe          | **Person B --- JWT                |
| Integration**                     | Authentication**                  |
+-----------------------------------+-----------------------------------+
| **Initialise MediaPipe Pose**     | **Password hashing**              |
|                                   |                                   |
| import mediapipe as mp. mp_pose = | from passlib.context import       |
| mp.solutions.pose. pose =         | CryptContext. pwd_context =       |
| mp_pose.Pose(model_complexity=1,  | Cryp                              |
| min_detection_confidence=0.7,     | tContext(schemes=\[\'bcrypt\'\]). |
| min_tracking_confidence=0.5).     | pwd_context.hash(\'password\') to |
| mp_draw =                         | store.                            |
| mp.solutions.drawing_utils.       | pwd_context.verify(\'password\',  |
| model_complexity=1 is the         | stored_hash) to check login.      |
| balanced option --- 0 is fastest  | NEVER store plain text passwords. |
| but less accurate, 2 is most      | Add to POST /users/register       |
| accurate but slow.                | endpoint.                         |
|                                   |                                   |
| **Run inference per frame**       | **Token creation**                |
|                                   |                                   |
| CRITICAL: MediaPipe needs RGB not | from jose import jwt. SECRET_KEY  |
| BGR. rgb = cv2.cvtColor(frame,    | in .env (generate with: python -c |
| cv2.COLOR_BGR2RGB).               | \'import secrets;                 |
| rgb.flags.writeable = False.      | print(secrets.token_hex(32))\').  |
| results = pose.process(rgb).      | create_access_token(user_id)      |
| rgb.flags.writeable = True.       | returns jwt.encode({\'sub\':      |
| Setting writeable=False before    | str(user_id), \'exp\':            |
| and True after is a performance   | utcnow()+timedelta(hours=24)},    |
| optimisation that prevents a data | SECRET_KEY, algorithm=\'HS256\'). |
| copy.                             |                                   |
|                                   | **Login endpoint**                |
| **Extract landmark coordinates**  |                                   |
|                                   | POST /auth/login takes email +    |
| if results.pose_landmarks: lm =   | password in JSON body. Fetch user |
| results.pose_landmarks.landmark.  | from DB by email. If not found →  |
| lm\[m                             | 401. pwd_context.verify password  |
| p_pose.PoseLandmark.LEFT_KNEE\].x | → if fail → 401. If pass → return |
| gives normalised x (0.0--1.0).    | {access_token, token_type:        |
| Multiply by frame width for pixel | \'bearer\'}.                      |
| x. Same for y with frame height.  |                                   |
| Always check lm\[idx\].visibility | **Token verification dependency** |
| \> 0.5 before using any landmark. |                                   |
|                                   | async def get_current_user(token: |
| **Draw the skeleton**             | str = Depends(oauth2_scheme), db  |
|                                   | = Depends(get_db)): decode JWT,   |
| mp_draw.draw_landmarks(frame,     | extract user_id, fetch user from  |
| results.pose_landmarks,           | DB, return user object. If any    |
| mp_pose.POSE_CONNECTIONS,         | step fails → raise                |
| mp_                               | HTTPException(401).               |
| draw.DrawingSpec(color=(0,255,0), |                                   |
| thickness=2, circle_radius=3),    | **Protect all workout endpoints** |
| mp_draw                           |                                   |
| .DrawingSpec(color=(255,255,255), | Add current_user: User =          |
| thickness=2)). First DrawingSpec  | Depends(get_current_user)         |
| is for landmark circles, second   | parameter to POST /workouts, POST |
| is for connection lines.          | /sessions, GET /history. The      |
|                                   | user_id for new records comes     |
| **Serialise landmarks to dict**   | from the token --- never trust    |
|                                   | the request body for this.        |
| Write extract_landmarks(results,  |                                   |
| frame_w, frame_h) that returns a  | **User profile endpoint**         |
| list of 33 dicts: \[{id, x_px,    |                                   |
| y_px, x_norm, y_norm,             | POST /users/register creates      |
| visibility}\]. This clean format  | user. GET /users/me returns       |
| is what everything else in the    | current user profile using the    |
| project will consume. Do not pass | auth token. Test the full flow:   |
| raw MediaPipe objects to other    | register → login → get token →    |
| functions.                        | call protected endpoint → verify  |
|                                   | it works.                         |
| **Handle missing person**         |                                   |
|                                   |                                   |
| If results.pose_landmarks is None |                                   |
| (person left frame or poor        |                                   |
| detection): return an empty list  |                                   |
| from extract_landmarks. Every     |                                   |
| downstream function must handle   |                                   |
| empty input gracefully with an    |                                   |
| early return.                     |                                   |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ ---------------------------------
  **Topic**         **What to Study**              **Where to Study**

  **MediaPipe Pose  mp.solutions.pose.Pose         developers.google.com/mediapipe
  (A)**             parameters: model_complexity   --- Pose section. Read the Python
                    (0/1/2),                       solution guide fully.
                    min_detection_confidence,      
                    min_tracking_confidence,       
                    static_image_mode (False for   
                    video). results object:        
                    pose_landmarks,                
                    pose_world_landmarks.          
                    NormalizedLandmarkList         
                    structure.                     

  **All 33 landmark Draw a stick figure and label  MediaPipe Pose landmark diagram
  IDs (A)**         every landmark with its ID     --- search \'mediapipe pose
                    number. Know by memory:        landmarks 33\' and save the
                    shoulders (11,12), elbows      image.
                    (13,14), wrists (15,16), hips  
                    (23,24), knees (25,26), ankles 
                    (27,28). This saves hours of   
                    looking things up later.       

  **Visibility vs   Each landmark has .visibility  MediaPipe source code:
  presence (A)**    (0--1, how confident the model pose_connections and landmark_pb2
                    is the landmark is in frame)   definitions
                    and .presence (0--1, how       
                    confident it is the landmark   
                    exists at all). Always gate on 
                    .visibility \> 0.5 before any  
                    calculation. Values below this 
                    are unreliable.                

  **passlib library CryptContext, bcrypt scheme,   passlib docs: quickstart page
  (B)**             hash(), verify(), why bcrypt   
                    is preferred (adaptive cost,   
                    built-in salt). Why MD5 and    
                    SHA are wrong for passwords.   

  **JWT tokens      What JSON Web Token is:        jwt.io --- introduction +
  (B)**             header.payload.signature.      debugger. python-jose docs on
                    Claims: sub (subject/user_id), PyPI.
                    exp (expiry timestamp), iat    
                    (issued at). How HMAC-SHA256   
                    signing works conceptually.    
                    Why tokens expire. python-jose 
                    library: encode, decode.       

  **FastAPI         OAuth2PasswordBearer,          FastAPI docs: Security section
  security (B)**    Depends() injection, how       --- OAuth2 with Password and
                    HTTPException with 401 and     Bearer
                    WWW-Authenticate header works, 
                    creating a reusable            
                    get_current_user dependency    
                    that other endpoints can       
                    inject.                        
  ----------------- ------------------------------ ---------------------------------

+-----------------------------------------------------------------------+
| **PHASE 4: JOINT ANGLE ENGINE & REP STATE MACHINE**                   |
|                                                                       |
| Duration: Week 7--8 (Days 43--56) \| Person A: angles + rep counting. |
| Person B: WebSocket server.                                           |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

The joint angle calculation function is the mathematical core that every
other feature depends on. Person A builds it with full understanding of
the vector geometry, then builds the rep-counting state machine with
hysteresis. Person B builds the WebSocket server that will stream live
frame data to the React frontend in later phases.

**The Joint Angle Formula --- Step by Step**

Three landmarks define an angle. B is the joint (the vertex). A and C
are the two segments meeting at B. For a knee angle: A = hip, B = knee,
C = ankle.

Step 1 --- Create two vectors: v1 = (A.x - B.x, A.y - B.y) and v2 =
(C.x - B.x, C.y - B.y). Each vector points from the joint outward along
one bone.

Step 2 --- Dot product: dot = v1\[0\]\*v2\[0\] + v1\[1\]\*v2\[1\]. This
single number encodes how aligned the two vectors are.

Step 3 --- Magnitudes: mag1 = sqrt(v1\[0\]\^2 + v1\[1\]\^2), same for
mag2. Guards: if mag1==0 or mag2==0, return 180.0 (straight) to avoid
division by zero.

Step 4 --- Cosine: cos_angle = dot / (mag1 \* mag2). Clamp: cos_angle =
np.clip(cos_angle, -1.0, 1.0). Without clipping, floating-point errors
produce values like 1.0000001 that make arccos crash.

Step 5 --- Angle in degrees: angle = np.degrees(np.arccos(cos_angle)).

Interpretation: fully straight knee (standing) ≈ 170--180°. Fully bent
knee (deep squat bottom) ≈ 65--90°. Use this understanding to set all
thresholds.

**The Rep State Machine --- Hysteresis Explained**

A naive counter: if angle \< 90: state = DOWN. if angle \> 90: state =
UP. count++. Problem: if angle hovers at 90 due to sensor noise, it
triggers dozens of counts per second.

Solution --- hysteresis: use TWO thresholds with a gap between them.
Going DOWN: only transition to DOWN state when angle drops BELOW
down_threshold (e.g., 90). Going UP: only transition to UP state when
angle rises ABOVE up_threshold (e.g., 155). The gap between 90 and 155
prevents noise-triggered transitions. A rep increments only on
UP→DOWN→UP cycle.

+-----------------------------------+-----------------------------------+
| **Person A --- Angles & State     | **Person B --- WebSocket Server** |
| Machine**                         |                                   |
+-----------------------------------+-----------------------------------+
| **Build calculate_angle(a, b,     | **Understand WebSocket vs HTTP**  |
| c)**                              |                                   |
|                                   | HTTP: client asks, server         |
| Each argument is a dict {x, y} in | responds, connection closes.      |
| pixel coordinates. Implement the  | WebSocket: connection stays open  |
| 5 steps above using numpy. Return | permanently. Server can push data |
| float degrees. Write a test       | to client at any time without     |
| first: three points at (0,0),     | client asking. This is how you    |
| (0,10), (10,10) should give       | will stream 15+ frames per second |
| exactly 90.0 degrees.             | of pose data to React.            |
|                                   |                                   |
| **Verify all exercise angles**    | **WebSocket endpoint in FastAPI** |
|                                   |                                   |
| Sit in front of webcam. Do a      | \@app                             |
| squat slowly. Watch the knee      | .websocket(\'/ws/{session_id}\'). |
| angle value on screen. At         | async def                         |
| standing: should be 160--175°. At | websocket_endpoint(websocket:     |
| bottom: should be 70--95°. If     | WebSocket, session_id: str):      |
| values are inverted or wrong, you | await websocket.accept(). Then    |
| likely have A and C swapped. Fix  | loop: data = await                |
| the order.                        | websocket.receive_text(). Process |
|                                   | data. await                       |
| **RepCounter class**              | websocket.send_text(result).      |
|                                   | Handle WebSocketDisconnect        |
| class RepCounter with: self.state | exception for clean exit.         |
| = \'UP\', self.count = 0,         |                                   |
| self.down_threshold,              | **ConnectionManager class**       |
| self.up_threshold,                |                                   |
| self.last_transition_frame = 0.   | class ConnectionManager:          |
| Method update(angle, frame_num) → | self.active_connections:          |
| bool (True if rep completed).     | dict\[str, WebSocket\] = {}.      |
| Minimum 15 frames between state   | Methods: async connect(ws,        |
| transitions to prevent            | session_id) stores connection.    |
| double-counting.                  | disconnect(session_id) removes    |
|                                   | it. async send_to_session(data:   |
| **Exercise-specific thresholds**  | dict, session_id: str) calls      |
|                                   | webso                             |
| Squat: monitor knee angle,        | cket.send_text(json.dumps(data)). |
| down=90, up=155. Deadlift:        |                                   |
| monitor hip angle                 | **Define the frame message        |
| (shoulder-hip-knee), down=70,     | schema**                          |
| up=155. Bicep curl: monitor elbow |                                   |
| angle (shoulder-elbow-wrist),     | Agree with Person A on exact JSON |
| down=35, up=155. Push-up: monitor | exchanged per frame. Outgoing to  |
| elbow angle, down=90, up=155.     | frontend: {frame_id, timestamp,   |
| Lunge: monitor front knee,        | rep_count, state, form_score,     |
| down=90, up=155.                  | active_errors: \[{code, message,  |
|                                   | severity}\], left_angle,          |
| **Timestamp each state**          | right_angle, asymmetry_pct,       |
|                                   | tempo_phase, tempo_seconds}.      |
| Record the frame number and       | Write this in a shared            |
| time.time() at every state        | /docs/websocket_schema.md file.   |
| transition: entered_down_at,      |                                   |
| exited_down_at. This data feeds   | **Heartbeat mechanism**           |
| into tempo analysis in Phase 6.   |                                   |
| Store as instance variables       | Every 10 seconds, server sends    |
| updated by the update() method.   | {type: \'ping\'}. If client does  |
|                                   | not respond within 5 seconds,     |
| **Wire into webcam loop**         | close the connection and clean up |
|                                   | from ConnectionManager. Prevents  |
| In the main while loop: extract   | ghost connections accumulating on |
| landmarks, calculate relevant     | the server.                       |
| angle, call counter.update(angle, |                                   |
| frame_num), draw angle value on   | **Test with a simple client**     |
| frame, draw rep count on frame.   |                                   |
| Test: do 10 squats, verify        | Write a Python script (not React  |
| counter shows exactly 10.         | yet) using websockets library:    |
|                                   | asyncio.run(test()). Connect to   |
|                                   | ws://localhost:8000/ws/test123.   |
|                                   | Send fake frame JSON. Print       |
|                                   | responses. Confirm round-trip     |
|                                   | works before React integration.   |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ -----------------------
  **Topic**         **What to Study**              **Where to Study**

  **Vector          What a vector is (direction +  Khan Academy: Vectors
  mathematics (A)** magnitude). Vector subtraction section. Watch the dot
                    (A minus B). Dot product       product video
                    formula and what it means      specifically. 45
                    geometrically (projection).    minutes total.
                    Why dot product of             
                    perpendicular vectors is zero. 
                    Magnitude using Pythagorean    
                    theorem.                       

  **np.arccos and   What arccos returns (radians). NumPy docs: arccos,
  np.clip (A)**     np.degrees() conversion. Why   degrees, clip functions
                    np.clip(-1.0, 1.0) is required 
                    (floating-point domain error   
                    prevention). What happens      
                    without it (NaN output that    
                    silently breaks downstream).   

  **Finite state    State, transition, guard       Search: \'hysteresis
  machines (A)**    condition. How hysteresis      threshold state machine
                    creates a dead-band between    python\' --- read any
                    thresholds. Why two-threshold  clear blog post (20
                    designs prevent oscillation    min)
                    near a boundary. How to        
                    represent state as a string    
                    variable.                      

  **Python          \@dataclass decorator. Why it  Python docs:
  dataclasses (A)** is cleaner than a plain dict   dataclasses module ---
                    for structured data like       20 min read
                    landmarks. \_\_post_init\_\_   
                    for validation. asdict() for   
                    JSON serialisation.            

  **WebSocket       How the HTTP Upgrade handshake MDN: WebSockets API
  protocol (B)**    works. Full-duplex             overview page
                    communication. Frames and      
                    opcodes. ws:// vs wss://       
                    (TLS). Why it is better than   
                    long-polling for this use      
                    case.                          

  **FastAPI         WebSocket class methods:       FastAPI docs:
  WebSocket (B)**   accept(), receive_text(),      WebSockets section ---
                    receive_bytes(), send_text(),  full page including
                    send_json().                   manager example
                    WebSocketDisconnect exception. 
                    asyncio.gather for concurrent  
                    tasks. How to test WebSocket   
                    endpoints.                     
  ----------------- ------------------------------ -----------------------

+-----------------------------------------------------------------------+
| **PHASE 5: PERSONALISED BIOMECHANICAL CALIBRATION**                   |
|                                                                       |
| Duration: Week 9--10 (Days 57--70) \| Person A: calibration engine.   |
| Person B: REST session APIs.                                          |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

This is the feature that immediately separates KINESIS from every other
project. Instead of using fixed population-average thresholds (90
degrees for everyone), KINESIS measures each user\'s body proportions
from a 45-second calibration and computes personalised optimal angles.
Person B builds the complete session lifecycle API --- the endpoints
that manage starting, tracking, and ending a workout.

**Calibration --- The Biomechanical Rationale**

Why generic thresholds are wrong: a person with long femurs relative to
their torso physically cannot achieve the same knee angle at squat depth
as someone with short femurs. To hit parallel (hip crease below knee), a
long-femured person must lean their torso more forward. If you penalise
their torso lean with the same threshold as a short-femured person, you
are giving them wrong feedback. Published research in exercise science
(you can cite Powers, C.M. 2010 and Escamilla, R.F. 2001 on squat
biomechanics) establishes that body segment ratios significantly affect
ideal movement mechanics.

**Calibration Sequence --- What Person A Builds**

45-second guided sequence. The user sees instructions on screen and
follows them:

-   Stand still, upright, facing camera (5 seconds) --- measures
    standing height, shoulder width, hip width

-   Raise both arms to shoulder height (3 seconds) --- measures arm span
    ratio

-   Perform 3 slow bodyweight squats (20 seconds) --- captures natural
    squat mechanics

-   Perform 3 slow hip hinges / Romanian deadlift motion (15 seconds)
    --- captures hinge mechanics

-   Return to standing (2 seconds) --- final standing measurement

**Measurements Extracted and How**

-   **Torso-to-femur ratio:** shoulder_midpoint_y to hip_midpoint_y
    distance (torso length) divided by hip_midpoint_y to knee_midpoint_y
    distance (femur length). If ratio \> 1.3: short torso/long femur
    type → more forward lean is acceptable in squats.

-   **Shoulder width:** Pixel distance between LEFT_SHOULDER and
    RIGHT_SHOULDER in calibration standing frame.

-   **Hip width:** Pixel distance between LEFT_HIP and RIGHT_HIP. Used
    to scale all width-based threshold checks.

-   **Natural squat depth angle:** Median knee angle across the 3 squat
    bottom positions. This is the user\'s ACTUAL natural depth. If it is
    80°, their squat depth threshold is 80°+5° = 85° (not a generic
    90°).

-   **Personalised forward lean allowance:** Torso angle (shoulder-hip
    vertical) at natural squat bottom. If person naturally leans at 45°,
    their lean threshold is 45°+10° = 55°. Beyond that is excessive for
    THEM.

+-----------------------------------+-----------------------------------+
| **Person A --- Calibration        | **Person B --- Session Lifecycle  |
| Engine**                          | APIs**                            |
+-----------------------------------+-----------------------------------+
| **Calibration state machine**     | **POST /sessions/start**          |
|                                   |                                   |
| class CalibrationSession with     | Body: {exercise, target_sets,     |
| states: STANDING, ARMS_UP,        | reps_per_set}. Creates workout    |
| SQUATTING, HINGING, COMPLETE.     | row. Returns {session_id,         |
| Timer advances through states.    | websocket_url: /ws/{session_id}}. |
| On-screen text tells user what to | Frontend uses session_id to       |
| do. Each state collects landmarks | connect WebSocket and to save     |
| into a buffer.                    | reps.                             |
|                                   |                                   |
| **Segment ratio computation**     | **POST /sessions/{id}/reps**      |
|                                   |                                   |
| During STANDING state: each       | Body: {set_number, rep_number,    |
| frame, compute pixel distances    | form_score, tempo_eccentric_s,    |
| between shoulder pair and hip     | tempo_concentric_s, left_angle,   |
| pair and store in lists. After    | right_angle, asymmetry_pct,       |
| state exits: take medians.        | compensation_detected, errors:    |
| Compute torso_to_femur = torso_px | \[{code, severity, frame_count,   |
| / femur_px.                       | frames_total}\]}. Saves all rep   |
|                                   | data. Returns saved rep id.       |
| **Natural depth extraction**      |                                   |
|                                   | **PATCH /sessions/{id}/end**      |
| During SQUATTING state: track     |                                   |
| knee angle each frame. Find the   | Sets ended_at timestamp. Computes |
| minimum knee angle per squat      | avg_form_score from all reps in   |
| (deepest point). Collect across 3 | session. Computes avg_asymmetry.  |
| squats. Take median. This is the  | Saves to workouts table. Returns  |
| user\'s natural depth threshold,  | session summary.                  |
| not 90°.                          |                                   |
|                                   | **GET /sessions/{id}/detail**     |
| **PersonalProfile dataclass**     |                                   |
|                                   | Returns full session: all sets,   |
| \@dataclass class                 | all reps, all form_errors per     |
| PersonalProfile:                  | rep. Used by the post-workout     |
| torso_femur_ratio,                | detail view. Use SQLAlchemy eager |
| shoulder_width_px, hip_width_px,  | loading to avoid N+1 queries.     |
| squat_depth_threshold,            |                                   |
| squat_lean_threshold,             | **POST /users/{id}/profile**      |
| natural_hinge_angle. Method       |                                   |
| get_exercise_thresholds(exercise) | Saves calibration profile to      |
| returns dict of personalised      | user_profiles table. If profile   |
| angle limits.                     | already exists: UPDATE it         |
|                                   | (upsert). Returns saved profile.  |
| **Store profile in database**     | Called by Person A\'s calibration |
|                                   | engine after completion.          |
| After calibration complete: POST  |                                   |
| to /users/{id}/profile endpoint   | **GET /users/{id}/profile**       |
| (Person B\'s API). Store all      |                                   |
| measured values. Load from DB at  | Returns the user\'s calibration   |
| session start and pass to all     | profile. Called at session start  |
| form checkers. Profile is         | by the frontend so Person A\'s    |
| re-calibrated any time user       | form checkers can load            |
| wants.                            | personalised thresholds.          |
|                                   |                                   |
| **Fallback to defaults**          |                                   |
|                                   |                                   |
| If calibration is not complete    |                                   |
| (new user, first session): use    |                                   |
| population-average defaults.      |                                   |
| Display banner: \'Run calibration |                                   |
| for personalised form feedback\'. |                                   |
| This ensures system works even    |                                   |
| without calibration.              |                                   |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ----------------------------------- -----------------------
  **Topic**         **What to Study**                   **Where to Study**

  **Pixel distance  Euclidean distance =                NumPy docs:
  calculation (A)** sqrt((x2-x1)\^2 + (y2-y1)\^2).      linalg.norm. Basic
                    numpy.linalg.norm(\[dx, dy\]) is    geometry revision.
                    the numpy shortcut. Why we use      
                    pixel distances during calibration  
                    rather than normalised coordinates  
                    (normalised coords depend on frame  
                    size and perspective).              

  **Statistical     Why median is better for            NumPy docs: median
  median vs mean    calibration data (robust to         
  (A)**             outliers from detection glitches).  
                    numpy.median(). Collecting readings 
                    into a list across multiple frames  
                    then taking the median.             

  **Python          \@dataclass, field(),               Python docs:
  dataclasses (A)** default_factory, asdict(),          dataclasses --- full
                    astuple(). How to add methods to a  module documentation
                    dataclass. Why dataclasses are      
                    cleaner than namedtuple for mutable 
                    structured data.                    

  **SQLAlchemy      How to insert-or-update in          SQLAlchemy docs: insert
  upsert (B)**      SQLAlchemy: query first, update if  with
                    exists, insert if not. Or use       on_conflict_do_update
                    PostgreSQL ON CONFLICT DO UPDATE    (PostgreSQL-specific)
                    via                                 
                    insert().on_conflict_do_update().   
                    Why raw SQL upsert is sometimes     
                    cleaner.                            

  **FastAPI request How Pydantic validates incoming     FastAPI docs: Request
  validation (B)**  JSON automatically. Custom          Body --- extra data
                    validators with \@validator.        types section
                    Returning 422 Unprocessable Entity  
                    on validation failure. Union types  
                    and Optional fields.                

  **Biomechanics of Why limb proportions affect squat   NSCA (National Strength
  squat (A)**       mechanics. What valgus collapse is  and Conditioning
                    and why it happens. What \'hip      Association) has free
                    crease below parallel\' means       squat biomechanics
                    geometrically. Why ankle mobility   articles online. Search
                    affects knee travel. Read at least  \'squat biomechanics
                    one sports science overview.        limb length research\'.
  ----------------- ----------------------------------- -----------------------

+-----------------------------------------------------------------------+
| **PHASE 6: BILATERAL ASYMMETRY & TEMPO ANALYSIS**                     |
|                                                                       |
| Duration: Week 11--12 (Days 71--84) \| Person A: asymmetry + tempo.   |
| Person B: TimescaleDB + trajectory storage.                           |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

Two distinct innovations are built this phase. Bilateral asymmetry
scoring compares left and right joint angles simultaneously to detect
muscular imbalances --- something no existing student project does.
Tempo analysis measures the time spent in each phase of an exercise and
scores it against evidence-based targets from strength training
research. Person B replaces simple PostgreSQL storage for landmark data
with TimescaleDB hypertables --- the architectural signal that you
understand time-series data.

**Bilateral Asymmetry --- Technical Detail**

Asymmetry Index (AI) is a standard metric in sports biomechanics
research: AI = \|left_angle - right_angle\| / ((left_angle +
right_angle) / 2) × 100. This gives percentage asymmetry between sides.
Research threshold: AI \> 10--15% is clinically meaningful and
associated with elevated injury risk.

Per-rep: compute AI for the primary joint (both knees in squat, both
hips in deadlift) at the bottom of each rep. Store left_angle,
right_angle, asymmetry_pct in the reps table.

Per-session: compute session-average AI. If \> 10%: show warning. If
consistent across 3+ sessions: escalate to injury risk alert.

Directional flag: record WHICH side is consistently higher-angled.
\'Right knee angle is consistently 12% greater than left --- possible
left hip abductor weakness.\'

**Tempo Analysis --- The Phases**

Every rep has three distinct phases. Using the timestamps Person A
stored in the RepCounter in Phase 4:

-   **Eccentric phase:** Muscle lengthening under load. For squats: the
    descent. Duration = time from UP→DOWN transition to reaching minimum
    angle. Target for hypertrophy: 2--4 seconds. Below 1 second: too
    ballistic, higher injury risk.

-   **Isometric phase:** Pause at the end range. For squats: pause at
    the bottom before rising. Duration = time from minimum angle to
    beginning of ascent. Target: 0.5--2 seconds. Brief pause improves
    neuromuscular activation.

-   **Concentric phase:** Muscle shortening under load. For squats: the
    ascent. Duration = time from start of ascent to DOWN→UP transition.
    Target: 1--2 seconds. Faster concentrics are acceptable for power
    training.

+-----------------------------------+-----------------------------------+
| **Person A --- Asymmetry &        | **Person B --- TimescaleDB        |
| Tempo**                           | Trajectory Storage**              |
+-----------------------------------+-----------------------------------+
| **AsymmetryAnalyser class**       | **Why TimescaleDB for landmarks** |
|                                   |                                   |
| class AsymmetryAnalyser:          | Landmark data is time-series: 33  |
| analyse_rep(left_angle,           | landmarks × 3 values × 30fps ×    |
| right_angle) → dict with          | duration. Storing as PostgreSQL   |
| {ai_percent, dominant_side,       | rows is slow to query over time   |
| risk_level}. Risk levels: \'OK\'  | ranges. TimescaleDB hypertables   |
| (\<10%), \'WARNING\' (10--15%),   | auto-partition by time, making    |
| \'HIGH\' (\>15%). Maintain        | \'give me all knee angles for     |
| session history list.             | user X in the last 10 sessions\'  |
|                                   | orders of magnitude faster.       |
| **Collect both-side angles        |                                   |
| simultaneously**                  | **Create landmark hypertable**    |
|                                   |                                   |
| At rep bottom (DOWN state):       | In alembic migration: CREATE      |
| extract BOTH left_knee and        | TABLE landmark_frames (time       |
| right_knee angles in the same     | TIMESTAMPTZ NOT NULL, session_id  |
| frame. Pass both to               | INT, frame_id INT, landmark_id    |
| AsymmetryAnalyser. Do NOT average | INT, x_norm FLOAT, y_norm FLOAT,  |
| them --- store them separately    | visibility FLOAT). Then: SELECT   |
| and compare.                      | creat                             |
|                                   | e_hypertable(\'landmark_frames\', |
| **Session asymmetry trend**       | \'time\'). This partitions the    |
|                                   | table by time automatically.      |
| After each rep: append AI to      |                                   |
| session list. After each set:     | **Batch insert landmarks**        |
| compute set-average AI. If 3+     |                                   |
| consecutive sets show AI \> 10%   | Do not insert one row per         |
| on same side: fire                | landmark. Build a list of 33 rows |
| BILATERAL_IMBALANCE event with    | per frame and use                 |
| directional info.                 | session.bulk_insert_mappings().   |
|                                   | Call this every 10 frames (not    |
| **TempoAnalyser class**           | every frame) to reduce DB write   |
|                                   | pressure. Store to TimescaleDB    |
| class TempoAnalyser: uses         | asynchronously using a background |
| timestamps stored by RepCounter.  | queue.                            |
| Properties: eccentric_duration,   |                                   |
| isometric_duration,               | **Time-series query endpoint**    |
| concentric_duration. Method       |                                   |
| score_tempo(exercise) compares    | GET                               |
| measured durations to target      | /sessio                           |
| ranges and returns {phase,        | ns/{id}/angles?landmark=LEFT_KNEE |
| measured, target, ok: bool} per   | returns the angle time-series for |
| phase.                            | one landmark across a session.    |
|                                   | Uses: SELECT time, y_norm FROM    |
| **Target tempo ranges per         | landmark_frames WHERE             |
| exercise**                        | session_id=X AND landmark_id=Y    |
|                                   | ORDER BY time. Returns as list of |
| Squat: eccentric 2--4s, iso       | {timestamp, value} for Recharts.  |
| 0.5--1.5s, concentric 1--2s.      |                                   |
| Deadlift: eccentric 2--3s, iso    | **Add compression policy**        |
| 0.5s, concentric 1--2s. Bicep     |                                   |
| curl: eccentric 2--3s, iso 0.5s,  | SELECT                            |
| concentric 1s. These come from    | add_compre                        |
| NSCA strength training guidelines | ssion_policy(\'landmark_frames\', |
| --- cite them.                    | INTERVAL \'7 days\'). TimescaleDB |
|                                   | automatically compresses data     |
| **Surface both in WebSocket       | older than 7 days. Reduces        |
| frame**                           | storage 10×. Shows you understand |
|                                   | production data management.       |
| Add to the per-frame JSON:        |                                   |
| {asymmetry: {ai_pct,              | **Retention policy**              |
| dominant_side, risk}, tempo:      |                                   |
| {phase, eccentric_s, isometric_s, | SELECT                            |
| concentric_s, eccentric_ok,       | add_rete                          |
| concentric_ok}}. Person B reads   | ntion_policy(\'landmark_frames\', |
| this in the frontend.             | INTERVAL \'90 days\').            |
|                                   | Auto-deletes landmark data older  |
|                                   | than 90 days. Only aggregated     |
|                                   | rep-level data is kept forever.   |
|                                   | Document this architectural       |
|                                   | decision in /docs.                |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------------- -----------------------
  **Topic**         **What to Study**                     **Where to Study**

  **Bilateral       How AI% formula works. Why absolute   Search: \'bilateral
  asymmetry index   difference is not enough (a 10-degree asymmetry index formula
  (A)**             difference means more at a small      sports science\' ---
                    angle than a large one). Research     read 1--2 sports
                    threshold of 10--15% from sports      medicine papers. Cite
                    science literature.                   them.

  **Python time     time.time() for Unix timestamps.      Python docs: time
  module (A)**      time.perf_counter() for               module --- time() and
                    high-resolution timing (better for    perf_counter()
                    sub-second durations like tempo       
                    phases). Difference between two       
                    perf_counter readings gives elapsed   
                    seconds.                              

  **TimescaleDB     What a hypertable is (partitioned by  TimescaleDB docs:
  basics (B)**      time). create_hypertable() call. What Getting Started ---
                    chunk interval means. How TimescaleDB first 3 pages
                    improves time-range queries. How to   
                    install the extension (already done   
                    in Phase 1).                          

  **Bulk insert     session.bulk_insert_mappings(Model,   SQLAlchemy docs: Bulk
  SQLAlchemy (B)**  list_of_dicts) vs inserting one by    Operations section
                    one. Why batch inserts are 10--100×   
                    faster. When to use it vs regular     
                    add/commit.                           

  **Tempo and       What eccentric/concentric/isometric   NSCA: Essentials of
  training science  mean physiologically. Why slower      Strength Training ---
  (A)**             eccentrics create more hypertrophy    tempo chapter (or find
                    (time under tension). What TUT (time  free NSCA articles
                    under tension) means. NSCA position   online)
                    stand on resistance training.         
  ----------------- ------------------------------------- -----------------------

+-----------------------------------------------------------------------+
| **PHASE 7: COMPENSATORY MOVEMENT DETECTION**                          |
|                                                                       |
| Duration: Week 13--14 (Days 85--98) \| Person A: the core innovation. |
| Person B: React webcam + canvas overlay.                              |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

This is the most original and technically complex part of KINESIS.
Compensatory movement detection does not check individual joints in
isolation --- it checks correlated multi-joint patterns across a time
window to infer which primary muscle is fatiguing and how the body is
compensating. This is the feature that makes every interview
conversation different. Person B simultaneously builds the React webcam
component and the live skeleton Canvas overlay.

**Compensatory Detection --- Full Technical Explanation**

The key insight: when a primary muscle fatigues, the body unconsciously
recruits secondary muscles. This causes characteristic secondary joint
deviations that only appear as a COMBINED signature --- not as isolated
joint errors.

**Compensation Signature 1 --- Bicep Curl Shoulder Compensation**

Primary mover: biceps brachii. Compensation pattern: when biceps
approach failure, anterior deltoid fires to assist. Observable
signature: SIMULTANEOUSLY (a) wrist is rising (curl progressing), AND
(b) shoulder (landmark 11 or 12) is moving UPWARD (y decreasing), AND
(c) elbow is drifting FORWARD (x changing toward camera). All three must
co-occur across 5+ consecutive frames.

Implementation: in each frame within DOWN state, compute: shoulder_rise
= baseline_shoulder_y - current_shoulder_y (positive means rising).
elbow_drift = abs(current_elbow_x - baseline_elbow_x). If shoulder_rise
\> 0.04 \* torso_height AND elbow_drift \> 0.05 \* shoulder_width for 5+
consecutive frames → SHOULDER_COMPENSATION fired.

**Compensation Signature 2 --- Squat Glute Fatigue Compensation**

Primary mover: gluteus maximus. Compensation: as glutes fatigue, lower
back extensors take over hip extension. Observable signature: across
reps within a set, torso lean angle (shoulder-hip vertical angle)
INCREASES progressively. Rep 1 torso lean: 30°. Rep 5: 42°. Rep 8: 51°.
The trend --- not a single value --- is the signature.

Implementation: store torso_lean_angle at the bottom of every rep. Use
numpy.polyfit(\[1,2,3,\...n\], \[lean_rep1,\...lean_repN\], 1). If slope
\> +2.0 degrees per rep AND n \>= 4: GLUTE_COMPENSATION fired. Message:
\'Gluteal fatigue detected. Torso lean increasing across reps --- lower
back is compensating.\'

**Compensation Signature 3 --- Push-Up Pectoral Fatigue**

Primary mover: pectoralis major. Compensation: as pecs fatigue, elbow
flare increases to shift load toward triceps. Observable:
elbow_flare_angle (angle between elbow and body in horizontal) increases
across reps within a set.

Implementation: at bottom of each push-up (DOWN state), compute elbow
flare angle. Store per rep. If linear regression slope of flare angles
\> +3° per rep across 4+ reps: PECTORAL_COMPENSATION fired. Message:
\'Push-up shifting from chest-dominant to tricep-dominant. Consider
ending set.\'

+-----------------------------------+-----------------------------------+
| **Person A ---                    | **Person B --- React Webcam +     |
| CompensationDetector**            | Canvas**                          |
+-----------------------------------+-----------------------------------+
| **CompensationDetector class**    | **getUserMedia webcam component** |
|                                   |                                   |
| class                             | const videoRef = useRef(null).    |
| CompensationDetector(exercise).   | useEffect:                        |
| Maintains: self.rep_history =     | navigator.mediaDevice             |
| \[\] (list of per-rep             | s.getUserMedia({video:{width:640, |
| measurements), self.frame_buffer  | height:480}}).then(stream =\>     |
| = deque(maxlen=10) for            | videoRef.current.srcObject =      |
| current-frame multi-joint         | stream). Add constraints:         |
| tracking. Method                  | facingMode:\'user\',              |
| update_frame(landmarks, state)    | frameRate:{ideal:30}. Handle      |
| called each frame. Method         | NotAllowedError with try/catch    |
| analyse_rep_complete() called at  | and show \'Enable camera          |
| each rep end.                     | permission\'.                     |
|                                   |                                   |
| **Intra-rep multi-joint           | **Send frames to backend**        |
| tracking**                        |                                   |
|                                   | Use requestAnimationFrame loop    |
| In the frame_buffer: store a dict | (not setInterval --- rAF syncs to |
| each frame with ALL relevant      | display). Each iteration: draw    |
| joint positions. For bicep curl:  | videoRef onto a hidden canvas.    |
| {shoulder_y, elbow_x, wrist_y,    | Get base64 JPEG:                  |
| frame_time}. The buffer always    | hidde                             |
| contains the last 10 frames.      | nCanvas.toDataURL(\'image/jpeg\', |
| Check the signature conditions    | 0.6). Send via WebSocket:         |
| across the buffer --- not just    | s                                 |
| one frame.                        | ocket.send(JSON.stringify({frame: |
|                                   | base64, session_id})).            |
| **Inter-rep trend analysis**      |                                   |
|                                   | **Canvas overlay setup**          |
| In rep_history: after each rep,   |                                   |
| append the key measurement (torso | Two elements: \<video\> tag and   |
| lean, elbow flare). In            | \<canvas\> tag. CSS: container    |
| analyse_rep_complete(): if        | position:relative. canvas         |
| len(rep_history) \>= 4: run       | position:absolute, top:0, left:0, |
| numpy.polyfit. Check slope. Fire  | width:100%, height:100%,          |
| compensation event if threshold   | pointerEvents:none. The video     |
| exceeded.                         | shows the raw feed. The canvas is |
|                                   | transparent and drawn over it for |
| **Compensation event structure**  | annotations.                      |
|                                   |                                   |
| Every fired event is a dict:      | **Draw skeleton from landmarks**  |
| {type: \'COMPENSATION\', code:    |                                   |
| \'GLUTE_FATIGUE\', severity: 3,   | On each WebSocket message: const  |
| message: \'\...\', muscle:        | ctx =                             |
| \'Gluteus Maximus\',              | canv                              |
| recommendation: \'End set or      | asRef.current.getContext(\'2d\'). |
| reduce weight\'}. Severity 3 =    | ctx.clearRect(0,0,w,h). For each  |
| highest --- distinct from form    | landmark: ctx.beginPath();        |
| error severity.                   | ctx.arc(lm.x_norm\*w,             |
|                                   | lm.y_norm\*h, 5, 0, 2\*Math.PI).  |
| **Reset between sets**            | Colour: green if no active error, |
|                                   | red if landmark involved in       |
| self.rep_history = \[\] and       | active error. Draw connections    |
| self.frame_buffer.clear() at each | with ctx.lineTo.                  |
| new set. Compensation builds      |                                   |
| within a set. A new set starts    | **Colour-coded error display**    |
| fresh (rest restores some muscle  |                                   |
| capacity).                        | Active errors from WebSocket: red |
|                                   | alerts. Compensation events:      |
| **Add compensation to WebSocket   | purple alerts. Asymmetry warning: |
| output**                          | orange alert. Each alert has a    |
|                                   | fixed position on screen          |
| Extend the frame JSON: add        | (top-right stack). Auto-dismiss 3 |
| compensation_events: \[{code,     | seconds after the error clears    |
| message, muscle, severity}\].     | from incoming WebSocket data.     |
| Frontend shows these as a         |                                   |
| distinct alert type --- different | **Rep counter and state display** |
| colour from form errors (use      |                                   |
| purple for compensation, red for  | Large centred text showing        |
| form errors).                     | rep_count. Below it: current      |
|                                   | state (UP / DOWN / TRANSITION).   |
|                                   | Animate rep_count with a CSS      |
|                                   | scale keyframe when it            |
|                                   | increments. Show form_score as a  |
|                                   | coloured arc gauge (red 0--60,    |
|                                   | orange 60--80, green 80--100).    |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ------------------------- ------------------------------------- --------------------------------
  **Topic**                 **What to Study**                     **Where to Study**

  **Python deque (A)**      collections.deque(maxlen=N). How it   Python docs: collections.deque
                            auto-drops oldest elements when full. 
                            .appendleft(), .append(), iteration   
                            order. Why it is O(1) for append/pop  
                            vs O(N) for list insert at index 0.   

  **Multi-condition pattern How to check that multiple conditions Think through this logically ---
  detection (A)**           are ALL true across a sliding window  no special resource. Pattern:
                            of frames. Counting how many of the   sum(cond(f) for f in buffer) \>=
                            last N frames satisfy a condition.    threshold_count
                            Using sum() over a boolean list.      

  **Linear regression with  numpy.polyfit(x, y, 1) returns        NumPy docs: polyfit. Plot your
  polyfit (A)**             \[slope, intercept\]. What            test data first to visualise
                            negative/positive slope means. How to before writing detection logic.
                            interpret slope per-rep (degrees per  
                            rep of increase). What the residual   
                            tells you about linearity.            

  **getUserMedia API (B)**  MediaDevices.getUserMedia(),          MDN: Media Capture and Streams
                            constraints object (video             API --- getUserMedia() page
                            width/height/frameRate/facingMode),   
                            how to attach a stream to a video     
                            element, stopping tracks on component 
                            unmount (track.stop()), handling      
                            permission errors.                    

  **requestAnimationFrame   What rAF is and why it syncs to       MDN:
  (B)**                     monitor refresh rate (\~60fps). How   Window.requestAnimationFrame()
                            to cancel it on component unmount     
                            with cancelAnimationFrame(rafId). Why 
                            it is better than setInterval for     
                            video frame processing (no drift, no  
                            overrun).                             

  **Canvas 2D API (B)**     getContext(\'2d\'). clearRect.        MDN: Canvas API --- Drawing
                            beginPath, arc, fill (circles).       shapes tutorial. Read the full
                            moveTo, lineTo, stroke (lines).       page.
                            fillStyle, strokeStyle, lineWidth.    
                            globalAlpha for transparency. How to  
                            draw text with fillText and font      
                            property.                             
  ------------------------- ------------------------------------- --------------------------------

+-----------------------------------------------------------------------+
| **PHASE 8: MOVEMENT SIGNATURE FINGERPRINTING & FATIGUE DETECTION**    |
|                                                                       |
| Duration: Week 15--16 (Days 99--112) \| Person A: signature model +   |
| fatigue. Person B: dashboard charts + corrective engine.              |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

Movement signature fingerprinting is the research-level feature: after
enough sessions, KINESIS builds a statistical model of how YOU move
through each exercise --- your personal kinematic fingerprint. New reps
are compared to your own baseline using Dynamic Time Warping (DTW).
Person B builds the progress dashboard with all charts and the
corrective exercise recommendation engine.

**Movement Signature --- How DTW Works**

Dynamic Time Warping is an algorithm for measuring similarity between
two time-series that may differ in speed or length. This is critical for
reps: two correct squats by the same person may take different amounts
of time, but the SHAPE of the movement --- how the angle changes through
the range --- should be similar.

A rep is represented as a sequence of angle values sampled at regular
intervals, normalised to \[0,1\] length. Using fastdtw library:
distance, path = fastdtw(rep1_angles, rep2_angles). A small distance
means the two reps have similar shape. A large distance means they
diverged --- possible fatigue, distraction, or form breakdown.

Building the personal baseline: collect the 10 best-scored reps
(form_score \> 85) across the first 3--5 sessions. Compute pairwise DTW
distances. Store the mean baseline trajectory and the mean pairwise DTW
distance (the natural variability of that user\'s movement). Store in
database.

In live sessions: compute DTW distance of each incoming rep against the
stored baseline trajectory. If distance \> baseline_mean + 2.5 \*
baseline_std → anomalous rep detected. This is a 2.5-sigma deviation
from their personal norm.

+-----------------------------------+-----------------------------------+
| **Person A --- Fingerprint +      | **Person B --- Dashboard +        |
| Fatigue**                         | Corrective Engine**               |
+-----------------------------------+-----------------------------------+
| **RepTrajectory class**           | **Form score trend chart**        |
|                                   |                                   |
| class RepTrajectory: collects     | Recharts LineChart. X axis:       |
| (angle, timestamp) pairs during a | session date. Y axis:             |
| rep. On rep completion: normalise | avg_form_score (0--100). Fetch    |
| to fixed length of 50 points      | GET /users/{id}/sessions, map to  |
| using numpy.interp (resample from | {date, score}. One line per       |
| variable length to 50). Return as | exercise type in different        |
| numpy array.                      | colours. Reference line at y=80   |
|                                   | (good form threshold). This is    |
| **SignatureModel class**          | the most motivating chart ---     |
|                                   | shows improvement.                |
| class SignatureModel(user_id,     |                                   |
| exercise):                        | **Asymmetry history chart**       |
| self.baseline_trajectories = \[\] |                                   |
| (list of 50-point arrays). Method | Recharts BarChart or AreaChart. X |
| add_good_rep(trajectory): if      | axis: session number. Y axis: avg |
| form_score \> 85 and len \< 50:   | AI% per session. Horizontal       |
| append. Method                    | reference line at 10% (warning    |
| compute_baseline(): mean          | threshold). Colour bars: green    |
| trajectory = np.mean(stack,       | \<10%, orange 10--15%, red \>15%. |
| axis=0). baseline_variability =   | Shows whether imbalance is        |
| mean of all pairwise DTW          | improving.                        |
| distances.                        |                                   |
|                                   | **Tempo chart**                   |
| **DTW comparison**                |                                   |
|                                   | Recharts GroupedBarChart. X axis: |
| from fastdtw import fastdtw. from | session. Y axis: seconds. Three   |
| scipy.spatial.distance import     | bars per session: eccentric       |
| euclidean. distance, \_ =         | (blue), isometric (grey),         |
| fastdtw(incoming_rep,             | concentric (green). Reference     |
| baseline_mean, dist=euclidean).   | range shown as error bars or      |
| if distance \> baseline_mean +    | shaded regions. Shows user        |
| 2.5 \* baseline_std: fire         | whether their tempo is in the     |
| SIGNATURE_DEVIATION event.        | target zone.                      |
|                                   |                                   |
| **Persist signature to database** | **Error frequency breakdown**     |
|                                   |                                   |
| Store baseline_mean as a JSON     | Recharts BarChart. GET            |
| array in a new table:             | /users/{id}/common-errors returns |
| movement_signatures (id, user_id, | top 8 error codes with counts.    |
| exercise, baseline_trajectory     | Display sorted descending.        |
| JSON, baseline_variability,       | Clicking a bar opens a modal      |
| sample_count, updated_at). Load   | showing the corrective            |
| at session start.                 | prescription (next task).         |
|                                   |                                   |
| **FatigueDetector class**         | **Corrective exercise engine**    |
|                                   |                                   |
| class FatigueDetector:            | Build a Python dict in            |
| within_set_scores = \[\]. After   | backend/correctives.py:           |
| each rep: append form_score. If   | CORRECTIVES = { \'KNEE_VALGUS\':  |
| len \>= 3: np.polyfit(\[1..n\],   | {cause: \'Hip abductor weakness   |
| scores, 1) → slope. slope \<      | (Gluteus Medius)\', cues:         |
| -4.0: FATIGUE_WARNING. slope \<   | \[\'Push knees outward\',         |
| -8.0: FATIGUE_DANGER. Message:    | \'Imagine spreading floor         |
| \'Form declining across reps ---  | apart\'\], exercises:             |
| slope: X pts/rep.\'               | \[\'Clamshells 3×15\',            |
|                                   | \'Side-lying hip abduction\',     |
| **Combine all detectors in        | \'Monster walks\'\], reference:   |
| pipeline**                        | \'Mauntel et al. 2017\'}, \... }. |
|                                   | Add 10 entries covering all form  |
| In the main processing function,  | error codes. GET                  |
| run in order: 1)                  | /correctives/{error_code} returns |
| RepCounter.update(), 2)           | the full prescription.            |
| FormChecker.check(), 3)           |                                   |
| AsymmetryAnalyser.analyse_rep()   | **Per-rep timeline within         |
| on rep complete, 4)               | session**                         |
| TempoAnalyser.score() on rep      |                                   |
| complete, 5)                      | In session detail view: Recharts  |
| Co                                | BarChart where each bar is one    |
| mpensationDetector.update_frame() | rep, coloured by form_score.      |
| every frame, 6)                   | Tooltip on hover: shows all       |
| FatigueDetector.add() on rep      | errors that fired that rep,       |
| complete, 7)                      | duration, asymmetry%. Clicking a  |
| SignatureModel.compare() on rep   | bar shows compensation events for |
| complete. Package all outputs     | that rep.                         |
| into one WebSocket frame.         |                                   |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ -----------------------
  **Topic**         **What to Study**              **Where to Study**

  **Dynamic Time    What DTW is conceptually:      YouTube: \'Dynamic Time
  Warping (A)**     aligning two time-series that  Warping explained\' by
                    differ in speed. How the       Towards Data Science
                    distance matrix is computed.   (10 min video). Then
                    What the warping path          fastdtw GitHub README.
                    represents. Why Euclidean      
                    distance fails when sequences  
                    differ in length.              

  **Time-series     Why you normalise rep          NumPy docs: interp
  normalisation     trajectories to a fixed length 
  (A)**             (50 points).                   
                    numpy.interp(new_x, old_x,     
                    old_y) for resampling. What    
                    normalising by rep duration    
                    means vs frame-count           
                    normalisation.                 

  **Statistical     What a z-score is (value -     Khan Academy: Z-scores
  outlier detection mean) / std. What 2.5 standard and the empirical rule
  (A)**             deviations means for outlier   
                    probability (\~1.2% of normal  
                    population). Why 2.5 sigma is  
                    a reasonable alert threshold.  

  **Recharts        ReferenceArea, ReferenceLine,  recharts.org --- API
  advanced (B)**    ComposedChart (mixing line and reference for each
                    bar). Custom Tooltip           component used
                    component. ResponsiveContainer 
                    auto-sizing. How to pass       
                    complex data structures as the 
                    data prop.                     

  **React Router v6 BrowserRouter, Routes, Route,  React Router docs:
  (B)**             Link, NavLink, useNavigate,    Feature Overview ---
                    useParams. How to create a     v6. 30 min read.
                    /dashboard, /session/:id,      
                    /history route structure.      
                    Nested routes for the          
                    dashboard layout.              

  **Knowledge base  Why a plain Python dict is a   No external resource
  design (B)**      valid and defensible           --- design it yourself
                    \'corrective recommendation    and document your
                    engine\' for this scope. When  decisions in /docs.
                    you would upgrade to a graph   
                    database (Neo4j) in a          
                    production system. How to      
                    structure the corrective dict  
                    for easy maintenance.          
  ----------------- ------------------------------ -----------------------

+-----------------------------------------------------------------------+
| **PHASE 9: INTEGRATION, TESTING & END-TO-END FLOW**                   |
|                                                                       |
| Duration: Week 17--18 (Days 113--126) \| Both people --- everything   |
| connected and verified                                                |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

Every piece built in Phases 1--8 now gets connected into one working
system. This phase exists specifically for finding and fixing the bugs
that only appear when everything runs together. The full user journey
must work without failure across 3 different exercises and 3 different
people with different body types.

**GOALS BY END OF PHASE**

-   Full user journey works: register → login → calibrate → start
    session → live feedback → rep saved → session end → dashboard
    updated

-   Compensatory detection tested on real humans doing intentionally
    tired reps

-   Bilateral asymmetry fires when user intentionally squats with one
    knee more inward

-   DTW signature deviation fires after a user\'s form changes
    mid-session

-   WebSocket stream stable for 15+ minutes without dropping or memory
    leaking

-   All database tables contain correct data after a full session

-   Unit tests written for: calculate_angle, RepCounter,
    AsymmetryAnalyser, FatigueDetector

+-----------------------------------+-----------------------------------+
| **Person A --- ML Testing**       | **Person B --- Integration & API  |
|                                   | Tests**                           |
+-----------------------------------+-----------------------------------+
| **Unit test calculate_angle**     | **End-to-end API test script**    |
|                                   |                                   |
| pytest: test right angle = 90°.   | Write a Python script using httpx |
| Straight line = 180°. Obtuse      | library: register user → login →  |
| triangle = specific expected      | get token → GET /users/me → POST  |
| value. Test with visibility 0     | /sessions/start → POST            |
| (should return None or default).  | /sessions/id/reps (10 times) →    |
| Test with identical points (zero  | PATCH /sessions/id/end → GET      |
| vector --- should not crash).     | /sessions/id/detail. Assert each  |
|                                   | response is correct.              |
| **Unit test RepCounter**          |                                   |
|                                   | **WebSocket stability test**      |
| Mock a sequence of angle readings |                                   |
| that simulate 5 squats:           | Write asyncio test: connect       |
| \[170,150,130,                    | WebSocket, send 1000 fake frames  |
| 100,85,90,110,140,165,170,\...\]. | over 60 seconds. Count dropped    |
| Assert count == 5. Test edge      | messages. Assert \< 1% drop rate. |
| cases: angle hovers at threshold, | Check memory usage does not grow  |
| very fast transitions.            | (no leaks in ConnectionManager).  |
|                                   |                                   |
| **Unit test AsymmetryAnalyser**   | **Database consistency test**     |
|                                   |                                   |
| Test: left=90, right=90 → AI=0%,  | After a full simulated session:   |
| \'OK\'. left=85, right=100 →      | verify rep count in DB matches    |
| AI=16.4%, \'HIGH\'. Assert        | what was sent. Verify form_errors |
| dominant_side is \'RIGHT\' in     | rows match error count in reps.   |
| second case.                      | Verify avg_form_score in sets     |
|                                   | table matches manual calculation  |
| **Real-human test protocol**      | over reps.                        |
|                                   |                                   |
| Person A tests on themselves: do  | **Frontend error handling**       |
| 3 sets of 10 squats, last set to  |                                   |
| fatigue. Verify: rep counter      | Test: camera permission denied →  |
| accurate, fatigue warning fires   | show clear message, not white     |
| by rep 7--8, form score declines  | screen. WebSocket disconnects     |
| in last 2 reps. Film the session  | mid-session → show reconnecting   |
| for demo video.                   | banner, auto-reconnect after 2    |
|                                   | seconds. Backend returns 500 →    |
| **Test compensation detection**   | show \'Processing error, try      |
|                                   | again\' toast.                    |
| Do 3 sets of bicep curls. In the  |                                   |
| final set, intentionally shrug    | **Add database indexes**          |
| the shoulder on each curl. Verify |                                   |
| SHOULDER_COMPENSATION fires.      | Add index=True to                 |
| Document the frame count it takes | workout.user_id, reps.set_id,     |
| to trigger.                       | form_errors.rep_id,               |
|                                   | landmark_frames.session_id. Run   |
| **Refactor to clean pipeline      | EXPLAIN ANALYZE on the            |
| class**                           | /sessions/{id}/detail query       |
|                                   | before and after. Document the    |
| package ml/ as a proper Python    | speedup in /docs/performance.md.  |
| module. Create ml/pipeline.py     |                                   |
| with class                        | **CORS and security audit**       |
| KinesisPipeline(user_profile,     |                                   |
| exercise). Single method          | Confirm: all protected endpoints  |
| process_frame(frame) →            | return 401 without token. CORS    |
| FrameResult dataclass. The        | only allows your frontend origin. |
| FastAPI background task calls     | Uploaded file type validation     |
| only this one method.             | rejects non-video files. JWT      |
|                                   | tokens with expired exp are       |
|                                   | rejected.                         |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------------------- -----------------------
  **Topic**         **What to Study**                           **Where to Study**

  **pytest          def test\_\*, assert statements, pytest     pytest docs: Getting
  fundamentals      fixtures, conftest.py for shared fixtures,  Started and How-to
  (Both)**          parametrize for running one test with       guides --- first 4
                    multiple inputs, running with pytest -v for sections
                    verbose output.                             

  **httpx for API   httpx.Client() for synchronous requests.    httpx docs: quickstart
  testing (B)**     AsyncClient for async tests. How to set     
                    Authorization headers. How to test          
                    multipart file upload.                      

  **Python logging  logging.getLogger(\_\_name\_\_).            Python docs: logging
  module (Both)**   logging.basicConfig(level=logging.DEBUG).   HOWTO
                    Log levels: DEBUG, INFO, WARNING, ERROR,    
                    CRITICAL. Why print() is wrong for          
                    production code and logging is right.       

  **Memory          tracemalloc module for Python memory        Python docs:
  profiling (B)**   snapshots. How to detect memory leaks in    tracemalloc
                    WebSocket handlers. Checking that           
                    ConnectionManager correctly removes         
                    disconnected clients.                       

  **Browser         Network tab → WS filter shows all WebSocket Chrome DevTools:
  DevTools (B)**    frames sent and received. Console for       Network panel
                    JavaScript errors. Performance tab for      documentation
                    rendering bottlenecks. Application tab for  
                    localStorage and cookies.                   
  ----------------- ------------------------------------------- -----------------------

+-----------------------------------------------------------------------+
| **PHASE 10: DEPLOYMENT, POLISH & DOCUMENTATION**                      |
|                                                                       |
| Duration: Week 19--20 (Days 127--140) \| Both --- live on the         |
| internet, documented, demo-ready                                      |
+-----------------------------------------------------------------------+

**What Happens in This Phase**

The application goes live with a public URL. Docker containerises
everything so it runs with one command anywhere. The GitHub README is
written to professional standard. A 3-minute demo video is recorded and
uploaded. By the end of this phase the project is ready for final-year
evaluation, resume submission, and recruiter review.

**GOALS BY END OF PHASE**

-   App deployed and accessible at a public URL, working from any
    browser

-   docker-compose up \--build starts the complete app from zero in one
    command

-   GitHub README: project name, one-line pitch, demo GIF, architecture
    diagram, tech stack, setup, research basis

-   3-minute demo video recorded: calibration → squat session → live
    alerts → compensation fires → dashboard

-   Technical report section: methodology, calibration math, DTW
    explanation, form rule citations

-   Project card on resume with live URL and GitHub link

+-----------------------------------+-----------------------------------+
| **Person A --- Docker Backend +   | **Person B --- Frontend Docker +  |
| Demo**                            | Cloud**                           |
+-----------------------------------+-----------------------------------+
| **Dockerfile for ML + FastAPI**   | **Dockerfile for React            |
|                                   | (multi-stage)**                   |
| FROM python:3.10-slim. RUN        |                                   |
| apt-get update && apt-get install | Stage 1: FROM node:18-alpine AS   |
| -y libgl1-mesa-glx libglib2.0-0   | builder. WORKDIR /app. COPY       |
| (OpenCV needs these on Linux).    | package\*.json. RUN npm install.  |
| COPY requirements.txt. RUN pip    | COPY . . RUN npm run build. Stage |
| install -r requirements.txt. COPY | 2: FROM nginx:alpine. COPY        |
| . /app. WORKDIR /app. CMD         | \--from=builder /app/dist         |
| \[\"uvicorn\",                    | /usr/share/nginx/html. COPY       |
| \"backend.main:app\",             | nginx.conf                        |
| \"\--host\", \"0.0.0.0\",         | /etc/nginx/conf.d/default.conf.   |
| \"\--port\", \"8000\"\]. Build    | nginx.conf: location /api         |
| and test locally: docker build -t | {proxy_pass http://backend:8000}  |
| kinesis-backend . && docker run   | and location / {try_files \$uri   |
| -p 8000:8000 kinesis-backend.     | \$uri/ /index.html} for React     |
|                                   | Router.                           |
| **Record the demo video**         |                                   |
|                                   | **docker-compose.yml**            |
| Use OBS Studio (free,             |                                   |
| cross-platform). Script: 00:00    | Services: backend (builds from    |
| --- open app, show login. 00:20   | ./backend, ports 8000:8000,       |
| --- run calibration sequence.     | env_file .env, volumes            |
| 00:50 --- start squat session,    | ./uploads:/app/uploads), frontend |
| show live skeleton and rep        | (builds from ./frontend, ports    |
| counter. 01:20 --- intentionally  | 80:80, depends_on backend), db    |
| cave knees, show KNEE_VALGUS      | (image:                           |
| alert. 01:40 --- do fatiguing     | t                                 |
| set, show GLUTE_COMPENSATION      | imescale/timescaledb:latest-pg15, |
| fire. 02:10 --- session end, show | volumes                           |
| dashboard with score trend. 02:40 | postgr                            |
| --- show asymmetry chart. 3:00    | es_data:/var/lib/postgresql/data, |
| --- end. Upload to YouTube        | env POSTGRES_DB POSTGRES_USER     |
| unlisted. Link in README.         | POSTGRES_PASSWORD). Networks: all |
|                                   | services on same internal         |
| **Technical documentation**       | network.                          |
|                                   |                                   |
| Create /docs/METHODOLOGY.md.      | **Deploy backend on Render**      |
| Document: (1) calibration formula |                                   |
| with the torso/femur ratio        | Create account at render.com. New |
| computation. (2) compensation     | Web Service → connect GitHub repo |
| detection logic for each pattern  | → select /backend → Runtime       |
| with threshold justification. (3) | Python → Build Command: pip       |
| DTW-based fingerprinting approach | install -r requirements.txt →     |
| with reference to fastdtw. (4)    | Start Command: uvicorn            |
| form rules with sports science    | backend.main:app \--host 0.0.0.0  |
| citations. This is your academic  | \--port \$PORT. Set environment   |
| paper equivalent.                 | variables in dashboard:           |
|                                   | DATABASE_URL, SECRET_KEY. Free    |
| **Performance benchmarking**      | tier has limitations on memory    |
|                                   | --- may need \$7/month Starter    |
| Measure and document: FPS with    | plan for MediaPipe.               |
| model_complexity=1 on standard    |                                   |
| laptop. Latency from movement to  | **Deploy frontend on Vercel**     |
| alert display. Memory usage after |                                   |
| 20-minute session. Rep counter    | vercel.com → New Project → Import |
| accuracy on 100-rep test. Add a   | GitHub repo → Framework: Vite →   |
| /docs/BENCHMARKS.md with real     | Root: frontend → Build: npm run   |
| numbers.                          | build → Output: dist. Set         |
|                                   | environment variable:             |
|                                   | VITE_API_URL=https://your         |
|                                   | -render-backend-url.onrender.com. |
|                                   | After deploy: update Render CORS  |
|                                   | allow_origins to include Vercel   |
|                                   | URL.                              |
|                                   |                                   |
|                                   | **README structure**              |
|                                   |                                   |
|                                   | Sections in order: (1) KINESIS    |
|                                   | --- one-line pitch in bold. (2)   |
|                                   | Demo GIF (record with             |
|                                   | ScreenToGif, 10 seconds, \<5MB).  |
|                                   | (3) The 5 innovations --- 5       |
|                                   | bullet points. (4) Architecture   |
|                                   | diagram (draw in draw.io, export  |
|                                   | as PNG). (5) Tech stack table.    |
|                                   | (6) Quick setup (docker-compose   |
|                                   | up). (7) Research basis --- 3     |
|                                   | cited papers. (8) Live demo link. |
|                                   | This README is what recruiters    |
|                                   | read first.                       |
+-----------------------------------+-----------------------------------+

**What to Study Before This Phase**

  ----------------- ------------------------------ -----------------------------------------
  **Topic**         **What to Study**              **Where to Study**

  **Docker          FROM, RUN, COPY, WORKDIR,      Docker official: Get Started guide (Parts
  fundamentals      EXPOSE, CMD, ENV instructions. 1--3 only). 2 hours.
  (Both)**          Multi-stage builds (AS builder 
                    pattern). .dockerignore file.  
                    docker build, docker run,      
                    docker ps, docker logs. Image  
                    vs container distinction.      

  **Docker Compose  services, image vs build,      Docker Compose: Compose file reference
  (B)**             ports, volumes (named and      --- services key. 1 hour.
                    bind-mount), environment,      
                    env_file, depends_on,          
                    networks. docker-compose up    
                    \--build, down, logs, ps.      

  **nginx           Serving static files from html nginx beginner guide on nginx.org --- 45
  configuration     dir. location blocks.          min read
  (B)**             proxy_pass for API forwarding. 
                    try_files for React Router     
                    support. gzip compression.     
                    add_header for CORS at nginx   
                    level (backup to FastAPI       
                    CORS).                         

  **Environment     How Render and Vercel handle   Render docs: environment variables. Vite
  variables in      env vars (dashboard UI). Why   docs: env variables.
  cloud (B)**       you NEVER commit .env to Git.  
                    How to use python-dotenv       
                    locally and os.environ in      
                    production. VITE\_ prefix for  
                    Vite env vars exposed to       
                    browser.                       

  **Writing a good  What a demo GIF is and how to  Browse
  README (Both)**   create one (ScreenToGif on     github.com/matiassingers/awesome-readme
                    Windows, Peek on Linux). How   for 10 minutes to see what good looks
                    to embed images in markdown.   like.
                    Making a badges row            
                    (shields.io). Writing clear    
                    installation steps that a      
                    stranger can follow.           
  ----------------- ------------------------------ -----------------------------------------

**Timeline Summary --- All 10 Phases**

  --------- --------------- ------------------- ------------------- ------------
  **Ph.**   **Topic**       **Person A          **Person B          **Weeks**
                            Milestone**         Milestone**         

  **1**     Setup & Env     OpenCV + MediaPipe  FastAPI             1--2
                            installed, webcam   hello-world + DB    
                            opens               created             

  **2**     OpenCV +        Live annotated      6 endpoints + all 6 3--4
            FastAPI         webcam feed working DB tables via       
                                                Alembic             

  **3**     MediaPipe +     33 landmarks drawn, JWT login +         5--6
            Auth            serialised to dict  protected endpoints 

  **4**     Angles + Rep    Squat reps counted  WebSocket server    7--8
            Counter         accurately with     streaming JSON      
                            hysteresis          frames              

  **5**     Calibration     Personal thresholds Session lifecycle   9--10
                            computed from body  REST APIs complete  
                            props                                   

  **6**     Asymmetry +     AI% per rep + tempo TimescaleDB         11--12
            Tempo           phase scoring live  hypertable for      
                                                trajectories        

  **7**     Compensation    All 3 compensation  React webcam +      13--14
            Detection       patterns detecting  canvas skeleton     
                            live                overlay             

  **8**     Signature +     DTW fingerprint +   Dashboard charts +  15--16
            Fatigue         fatigue slope       corrective engine   
                            working                                 

  **9**     Integration +   Unit tests + real   E2E test +          17--18
            Tests           human testing done  WebSocket stability 
                                                verified            

  **10**    Deploy + Polish Demo video +        Docker + Render +   19--20
                            methodology docs    Vercel live URL     
                            written                                 
  --------- --------------- ------------------- ------------------- ------------

**Your Resume Line**

+-----------------------------------------------------------------------+
| *Built KINESIS --- a biomechanics-aware fitness intelligence platform |
| that personalises exercise form thresholds to individual body         |
| proportions via geometric calibration, detects compensatory           |
| multi-joint movement patterns indicating primary muscle fatigue,      |
| computes bilateral asymmetry index per rep as an injury risk signal,  |
| measures exercise tempo against evidence-based targets, and builds a  |
| per-user movement signature using Dynamic Time Warping for            |
| session-to-session deviation detection --- deployed full-stack with   |
| FastAPI, TimescaleDB, React, live WebSocket streaming, and a          |
| longitudinal analytics dashboard.*                                    |
|                                                                       |
| **Tech: Python · MediaPipe · OpenCV · NumPy · SciPy · fastdtw ·       |
| FastAPI · TimescaleDB · SQLAlchemy · JWT · React · WebSockets ·       |
| Recharts · Docker**                                                   |
+-----------------------------------------------------------------------+

Build one phase at a time. Test it fully before moving to the next. The
calibration and compensation detection phases are the ones that will be
remembered in every interview.
