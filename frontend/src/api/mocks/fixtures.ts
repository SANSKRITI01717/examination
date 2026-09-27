import type {
  User,
  Exam,
  Question,
  Student,
  AnswerSheet,
  AnswerDetail,
  Anomaly,
  ReferenceDoc,
  ProcessingStatus,
  AnalyticsOverview,
  ExaminerAnalytics,
  QuestionAnalytics,
  ExamResults,
} from '../types'

// Realistic SVG handwritten page data URI so zoom/pan works out of the box without external assets
export const SAMPLE_PAGE_SVG = `data:image/svg+xml;utf8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200" style="background:#fcfbf7;font-family:Caveat, cursive, 'Comic Sans MS', sans-serif;">
  <defs>
    <pattern id="lines" width="100" height="32" patternUnits="userSpaceOnUse">
      <line x1="0" y1="31" x2="100" y2="31" stroke="#dbe4ee" stroke-width="1.2"/>
    </pattern>
    <filter id="pencil" x="0%" y="0%" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="3" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.5"/>
    </filter>
  </defs>

  <rect width="900" height="1200" fill="#faf8f2"/>
  <rect x="70" y="80" width="760" height="1040" fill="url(#lines)"/>
  <line x1="120" y1="50" x2="120" y2="1150" stroke="#fca5a5" stroke-width="1.5"/>

  <!-- Header -->
  <text x="140" y="70" font-size="22" font-weight="bold" fill="#1e293b">Q3. Explain the TCP three-way handshake.</text>

  <!-- Handwritten answer -->
  <g filter="url(#pencil)" fill="#1e3a8a" font-size="24">
    <text x="140" y="125">1. SYN Phase: The client initiates the TCP connection by sending</text>
    <text x="140" y="157">   a SYN packet to the server. It includes an Initial Sequence</text>
    <text x="140" y="189">   Number (ISN = x). No data payload is carried in this segment.</text>

    <!-- Diagram -->
    <line x1="200" y1="240" x2="200" y2="440" stroke="#1e3a8a" stroke-width="2.5"/>
    <line x1="600" y1="240" x2="600" y2="440" stroke="#1e3a8a" stroke-width="2.5"/>
    <text x="175" y="230" font-size="20" font-weight="bold">CLIENT</text>
    <text x="575" y="230" font-size="20" font-weight="bold">SERVER</text>

    <line x1="200" y1="270" x2="600" y2="310" stroke="#2563eb" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="340" y="285" font-size="18">SYN (Seq = x)</text>

    <line x1="600" y1="330" x2="200" y2="370" stroke="#2563eb" stroke-width="2"/>
    <text x="310" y="345" font-size="18">SYN-ACK (Seq = y, Ack = x + 1)</text>

    <line x1="200" y1="390" x2="600" y2="430" stroke="#2563eb" stroke-width="2"/>
    <text x="340" y="405" font-size="18">ACK (Seq = x + 1, Ack = y + 1)</text>

    <!-- Text continued -->
    <text x="140" y="480">2. SYN-ACK Phase: The server replies with SYN-ACK, acknowledging</text>
    <text x="140" y="512">   the client's ISN with Ack=x+1, and establishes its own ISN=y.</text>
    <text x="140" y="544">   State transitions: Server moves to SYN_RCVD.</text>

    <text x="140" y="605">3. ACK Phase: Client replies with ACK packet acknowledging</text>
    <text x="140" y="637">   server's ISN with Ack=y+1. Now connection is ESTABLISHED.</text>

    <text x="140" y="700">Purpose: Synchronize sequence numbers and verify both directions</text>
    <text x="140" y="732">can send and receive before sending application data.</text>
  </g>

  <!-- Stamp / Margins -->
  <rect x="740" y="50" width="80" height="40" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4"/>
  <text x="755" y="76" font-size="15" fill="#64748b">Page 2</text>
</svg>
`)}`

export const INITIAL_USERS: User[] = [
  {
    id: 1,
    email: 'admin@univ.edu',
    full_name: 'Prof. Ada Lovelace',
    role: 'admin',
    is_active: true,
    created_at: '2026-09-01T08:00:00Z',
  },
  {
    id: 2,
    email: 'examiner@univ.edu',
    full_name: 'Dr. Alan Turing',
    role: 'examiner',
    is_active: true,
    created_at: '2026-09-02T08:00:00Z',
  },
  {
    id: 3,
    email: 'moderator@univ.edu',
    full_name: 'Dean Grace Hopper',
    role: 'moderator',
    is_active: true,
    created_at: '2026-09-03T08:00:00Z',
  },
]

export const INITIAL_EXAMS: Exam[] = [
  {
    id: 1,
    title: 'Computer Networks & Distributed Systems',
    course_code: 'CS-402',
    exam_date: '2026-09-15',
    status: 'evaluation',
    settings: {
      ocr_low_conf_threshold: 0.80,
      ai_low_conf_threshold: 0.70,
      ai_disagreement_ratio: 0.30,
      too_fast_seconds: 10,
      z_threshold: 2.5,
      min_sample_size: 10,
      retrieval_top_k: 4,
      retrieval_min_score: 0.50,
    },
    created_at: '2026-09-10T10:00:00Z',
  },
  {
    id: 2,
    title: 'Operating Systems & Concurrency',
    course_code: 'CS-301',
    exam_date: '2026-09-18',
    status: 'draft',
    settings: {
      ocr_low_conf_threshold: 0.80,
      ai_low_conf_threshold: 0.70,
    },
    created_at: '2026-09-12T14:00:00Z',
  },
]

export const INITIAL_QUESTIONS: Question[] = [
  {
    id: 21,
    exam_id: 1,
    question_number: '1',
    text: 'Define latency, throughput, and jitter in packet switching.',
    max_marks: 5,
    evaluation_mode: 'standard',
    display_order: 1,
    rubric: {
      question_id: 21,
      criteria: [
        { id: 'c1', name: 'Latency definition', max_marks: 2, description: 'Time taken for a packet to travel source to destination' },
        { id: 'c2', name: 'Throughput definition', max_marks: 2, description: 'Rate of successful data delivery over communication channel' },
        { id: 'c3', name: 'Jitter definition', max_marks: 1, description: 'Variation in packet arrival delay' },
      ],
      guidance: 'Award partial credit if units or formulas are provided accurately.',
    },
  },
  {
    id: 22,
    exam_id: 1,
    question_number: '2',
    text: 'Explain the TCP three-way handshake with a state diagram and the role of each segment.',
    max_marks: 10,
    evaluation_mode: 'standard',
    display_order: 2,
    rubric: {
      question_id: 22,
      criteria: [
        { id: 'c1', name: 'SYN segment', max_marks: 2, description: 'Client initiates SYN with initial sequence number (ISN)' },
        { id: 'c2', name: 'SYN-ACK segment', max_marks: 2, description: 'Server responds with SYN-ACK acknowledging client ISN' },
        { id: 'c3', name: 'ACK segment', max_marks: 2, description: 'Client sends final ACK to complete connection' },
        { id: 'c4', name: 'Purpose & Sequence Numbers', max_marks: 2, description: 'Explains synchronization of sequence numbers and connection setup' },
        { id: 'c5', name: 'Diagram & Overall correctness', max_marks: 2, description: 'State transitions and diagram clearly labelled' },
      ],
      guidance: 'Accept alternative diagrams if message sequence and flags are clear.',
    },
  },
  {
    id: 23,
    exam_id: 1,
    question_number: '3',
    text: 'Explain Raft leader election and log replication guarantees compared to Multi-Paxos.',
    max_marks: 15,
    evaluation_mode: 'reference_grounded',
    display_order: 3,
    rubric: {
      question_id: 23,
      criteria: [
        { id: 'c1', name: 'Leader Election', max_marks: 5, description: 'Heartbeats, randomized election timeouts, vote solicitation' },
        { id: 'c2', name: 'Log Replication', max_marks: 5, description: 'AppendEntries RPC, commit index, consistency check' },
        { id: 'c3', name: 'Safety & Paxos Comparison', max_marks: 5, description: 'Election safety, leader completeness, comparison to Paxos phases' },
      ],
      guidance: 'Must reference Raft state machine safety invariants.',
    },
  },
]

export const INITIAL_STUDENTS: Student[] = [
  { id: 101, roll_number: 'CS2026-001', full_name: 'Alice Johnson', department: 'Computer Science' },
  { id: 102, roll_number: 'CS2026-002', full_name: 'Bob Smith', department: 'Computer Science' },
  { id: 103, roll_number: 'CS2026-003', full_name: 'Carol Davis', department: 'Information Technology' },
  { id: 104, roll_number: 'CS2026-004', full_name: 'David Lee', department: 'Computer Science' },
]

export const INITIAL_SHEETS: AnswerSheet[] = [
  {
    id: 501,
    exam_id: 1,
    student_id: 101,
    anon_code: 'S-0417',
    status: 'mapped',
    page_count: 3,
    created_at: '2026-09-15T09:00:00Z',
    student: INITIAL_STUDENTS[0],
    mapped: true,
    answers_total: 3,
    answers_marked: 1,
  },
  {
    id: 502,
    exam_id: 1,
    student_id: 102,
    anon_code: 'S-0418',
    status: 'mapped',
    page_count: 3,
    created_at: '2026-09-15T09:05:00Z',
    student: INITIAL_STUDENTS[1],
    mapped: true,
    answers_total: 3,
    answers_marked: 3,
  },
  {
    id: 503,
    exam_id: 1,
    student_id: 103,
    anon_code: 'S-0419',
    status: 'mapped',
    page_count: 3,
    created_at: '2026-09-15T09:10:00Z',
    student: INITIAL_STUDENTS[2],
    mapped: true,
    answers_total: 3,
    answers_marked: 1,
  },
  {
    id: 504,
    exam_id: 1,
    student_id: 104,
    anon_code: 'S-0420',
    status: 'mapped',
    page_count: 3,
    created_at: '2026-09-15T09:15:00Z',
    student: INITIAL_STUDENTS[3],
    mapped: true,
    answers_total: 3,
    answers_marked: 3,
  },
]

export const INITIAL_DOCUMENTS: ReferenceDoc[] = [
  {
    id: 1,
    exam_id: 1,
    question_id: 23,
    title: 'Raft Consensus Protocol & Fault Tolerance Guide.pdf',
    doc_type: 'guideline',
    status: 'indexed',
    chunk_count: 16,
    error: null,
    created_at: '2026-09-12T11:00:00Z',
  },
  {
    id: 2,
    exam_id: 1,
    question_id: 21,
    title: 'Networking Basics Official Answers.pdf',
    doc_type: 'official_answer',
    status: 'indexed',
    chunk_count: 8,
    error: null,
    created_at: '2026-09-12T11:30:00Z',
  },
]

// Detailed Workspace Answers (including low-confidence OCR case and flagged case)
export const INITIAL_ANSWERS: AnswerDetail[] = [
  // Answer 811: S-0417, Q1 (Already marked)
  {
    id: 811,
    exam_id: 1,
    anon_code: 'S-0417',
    question: {
      id: 21,
      question_number: '1',
      text: 'Define latency, throughput, and jitter in packet switching.',
      max_marks: 5,
      evaluation_mode: 'standard',
    },
    rubric: INITIAL_QUESTIONS[0].rubric!,
    pages: [{ id: 54, page_number: 1, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: 'Latency is round trip or one way delay. Throughput is data transferred per second. Jitter is latency variance.',
      verified_text: 'Latency is round trip or one way delay. Throughput is data transferred per second. Jitter is latency variance.',
      confidence: 0.94,
      review_required: false,
      verified: true,
    },
    ai: {
      status: 'done',
      latest: {
        id: 939,
        answer_id: 811,
        mode_requested: 'standard',
        mode_used: 'standard',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 5,
        max_marks: 5,
        confidence: 0.91,
        llm_confidence: 0.94,
        criteria: [
          { criterion_id: 'c1', criterion: 'Latency definition', max_marks: 2, awarded_marks: 2, reason: 'Correctly defines time delay.' },
          { criterion_id: 'c2', criterion: 'Throughput definition', max_marks: 2, awarded_marks: 2, reason: 'Correctly identifies transfer rate.' },
          { criterion_id: 'c3', criterion: 'Jitter definition', max_marks: 1, awarded_marks: 1, reason: 'Identifies latency variation.' },
        ],
        overall_reason: 'All three definitions are concise and accurate.',
        warnings: [],
        stale: false,
        created_at: '2026-09-19T09:20:00Z',
      },
    },
    evaluation: {
      id: 701,
      marks_awarded: 5,
      criterion_marks: { c1: 2, c2: 2, c3: 1 },
      comment: 'Excellent concise definitions.',
      source: 'ai_accepted',
      status: 'submitted',
      submitted_at: '2026-09-19T09:25:00Z',
      examiner: { id: 2, full_name: 'Dr. Alan Turing' },
    },
    marking_status: 'marked',
    final_marks: 5,
    final_source: 'examiner',
    navigation: {
      position: 1,
      total: 6,
      prev_answer_id: null,
      next_answer_id: 812,
    },
    student: INITIAL_STUDENTS[0],
  },

  // Answer 812: S-0417, Q2 (LOW CONFIDENCE OCR — Human Verification Required!)
  {
    id: 812,
    exam_id: 1,
    anon_code: 'S-0417',
    question: {
      id: 22,
      question_number: '2',
      text: 'Explain the TCP three-way handshake with a state diagram and the role of each segment.',
      max_marks: 10,
      evaluation_mode: 'standard',
    },
    rubric: INITIAL_QUESTIONS[1].rubric!,
    pages: [{ id: 55, page_number: 2, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: '1. SYN Phase: The clint initiates conection by sendng SYN packet with ISN=x. 2. SYN-ACK Phase: Server replies SYN-ACK with Ack=x+1, ISN=y. 3. ACK Phase: Client replies ACK with Ack=y+1. Connection established.',
      verified_text: null,
      confidence: 0.74, // Low confidence! < 0.80 threshold
      review_required: true,
      verified: false,
    },
    ai: {
      status: 'done',
      latest: {
        id: 940,
        answer_id: 812,
        mode_requested: 'standard',
        mode_used: 'standard',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 7.0,
        max_marks: 10,
        confidence: 0.74,
        llm_confidence: 0.86,
        criteria: [
          { criterion_id: 'c1', criterion: 'SYN segment', max_marks: 2, awarded_marks: 2, reason: 'States client sends SYN with initial sequence number.' },
          { criterion_id: 'c2', criterion: 'SYN-ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Mentions server response with SYN-ACK and sequence number.' },
          { criterion_id: 'c3', criterion: 'ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Mentions client acknowledgment with ACK.' },
          { criterion_id: 'c4', criterion: 'Purpose & Sequence Numbers', max_marks: 2, awarded_marks: 1, reason: 'Brief mention of purpose; missing detailed ISN negotiation rationale.' },
          { criterion_id: 'c5', criterion: 'Diagram & Overall correctness', max_marks: 2, awarded_marks: 0, reason: 'Diagram text representation could not be fully evaluated from OCR text.' },
        ],
        overall_reason: 'Covers SYN, SYN-ACK, and ACK steps. Human verification recommended due to handwriting OCR ambiguities.',
        warnings: ['LOW_OCR_CONFIDENCE'],
        stale: false,
        created_at: '2026-09-19T09:30:00Z',
      },
    },
    evaluation: null,
    marking_status: 'pending',
    final_marks: null,
    final_source: null,
    navigation: {
      position: 2,
      total: 6,
      prev_answer_id: 811,
      next_answer_id: 813,
    },
    student: INITIAL_STUDENTS[0],
  },

  // Answer 813: S-0417, Q3 (Reference Grounded question)
  {
    id: 813,
    exam_id: 1,
    anon_code: 'S-0417',
    question: {
      id: 23,
      question_number: '3',
      text: 'Explain Raft leader election and log replication guarantees compared to Multi-Paxos.',
      max_marks: 15,
      evaluation_mode: 'reference_grounded',
    },
    rubric: INITIAL_QUESTIONS[2].rubric!,
    pages: [{ id: 56, page_number: 3, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: 'In Raft, servers are Leader, Follower or Candidate. Leaders send periodic heartbeats. When election timeout fires, follower becomes candidate and asks for votes. Log entries are replicated using AppendEntries RPC. Paxos allows out of order log entries whereas Raft enforces strict prefix matching.',
      verified_text: null,
      confidence: 0.88,
      review_required: false,
      verified: true,
    },
    ai: {
      status: 'done',
      latest: {
        id: 941,
        answer_id: 813,
        mode_requested: 'reference_grounded',
        mode_used: 'reference_grounded',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 13.0,
        max_marks: 15,
        confidence: 0.89,
        llm_confidence: 0.92,
        criteria: [
          { criterion_id: 'c1', criterion: 'Leader Election', max_marks: 5, awarded_marks: 4.5, reason: 'Clearly explains candidate state, election timeouts, and votes according to Section 5.2 of Raft guide.' },
          { criterion_id: 'c2', criterion: 'Log Replication', max_marks: 5, awarded_marks: 4.5, reason: 'Correctly identifies AppendEntries and entry matching invariant.' },
          { criterion_id: 'c3', criterion: 'Safety & Paxos Comparison', max_marks: 5, awarded_marks: 4.0, reason: 'Accurately contrasts Raft contiguous log prefix with Paxos hole handling.' },
        ],
        overall_reason: 'Strong answer grounded in reference material. Minor depth missing on joint consensus configuration changes.',
        retrieval: { chunks_used: 4, top_score: 0.89 },
        warnings: [],
        stale: false,
        created_at: '2026-09-19T09:35:00Z',
      },
    },
    evaluation: null,
    marking_status: 'pending',
    final_marks: null,
    final_source: null,
    navigation: {
      position: 3,
      total: 6,
      prev_answer_id: 812,
      next_answer_id: 814,
    },
    student: INITIAL_STUDENTS[0],
  },

  // Answer 814: S-0419, Q2 (Flagged: AI Disagreement Anomaly!)
  {
    id: 814,
    exam_id: 1,
    anon_code: 'S-0419',
    question: {
      id: 22,
      question_number: '2',
      text: 'Explain the TCP three-way handshake with a state diagram and the role of each segment.',
      max_marks: 10,
      evaluation_mode: 'standard',
    },
    rubric: INITIAL_QUESTIONS[1].rubric!,
    pages: [{ id: 57, page_number: 2, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: 'TCP handshake establishes connection between two hosts. Step 1: SYN packet sent by client. Step 2: SYN-ACK returned by server. Step 3: ACK sent by client. Sequence numbers ensure ordered transmission.',
      verified_text: 'TCP handshake establishes connection between two hosts. Step 1: SYN packet sent by client. Step 2: SYN-ACK returned by server. Step 3: ACK sent by client. Sequence numbers ensure ordered transmission.',
      confidence: 0.92,
      review_required: false,
      verified: true,
    },
    ai: {
      status: 'done',
      latest: {
        id: 942,
        answer_id: 814,
        mode_requested: 'standard',
        mode_used: 'standard',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 8.5,
        max_marks: 10,
        confidence: 0.88,
        llm_confidence: 0.90,
        criteria: [
          { criterion_id: 'c1', criterion: 'SYN segment', max_marks: 2, awarded_marks: 2, reason: 'Client initiates connection with SYN.' },
          { criterion_id: 'c2', criterion: 'SYN-ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Server responds with SYN-ACK.' },
          { criterion_id: 'c3', criterion: 'ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Client completes handshake with ACK.' },
          { criterion_id: 'c4', criterion: 'Purpose & Sequence Numbers', max_marks: 2, awarded_marks: 1.5, reason: 'Explains ordered transmission.' },
          { criterion_id: 'c5', criterion: 'Diagram & Overall correctness', max_marks: 2, awarded_marks: 1, reason: 'Text descriptions are accurate.' },
        ],
        overall_reason: 'Clear explanation covering all three segments and their role.',
        warnings: [],
        stale: false,
        created_at: '2026-09-19T09:40:00Z',
      },
    },
    evaluation: {
      id: 702,
      marks_awarded: 2.0, // Significant deviation from AI (8.5 vs 2.0)
      criterion_marks: { c1: 0.5, c2: 0.5, c3: 0.5, c4: 0.5, c5: 0 },
      comment: 'Incomplete diagram.',
      source: 'manual',
      status: 'submitted',
      submitted_at: '2026-09-19T09:42:00Z',
      examiner: { id: 2, full_name: 'Dr. Alan Turing' },
    },
    marking_status: 'flagged',
    final_marks: 2.0,
    final_source: 'examiner',
    anomalies: [
      {
        id: 301,
        exam_id: 1,
        type: 'AI_DISAGREEMENT',
        severity: 'high',
        answer_id: 814,
        question_id: 22,
        examiner_id: 2,
        score: 6.5,
        details: {
          examiner_marks: 2.0,
          ai_marks: 8.5,
          difference: 6.5,
          ratio: 0.65,
        },
        status: 'open',
        note: 'Examiner awarded 2.0 while AI suggested 8.5 on verified high-confidence text.',
        detected_at: '2026-09-19T10:00:00Z',
      },
    ],
    navigation: {
      position: 4,
      total: 6,
      prev_answer_id: 813,
      next_answer_id: 815,
    },
    student: INITIAL_STUDENTS[2],
  },

  // Answer 815: S-0420, Q1 (Marked)
  {
    id: 815,
    exam_id: 1,
    anon_code: 'S-0420',
    question: {
      id: 21,
      question_number: '1',
      text: 'Define latency, throughput, and jitter in packet switching.',
      max_marks: 5,
      evaluation_mode: 'standard',
    },
    rubric: INITIAL_QUESTIONS[0].rubric!,
    pages: [{ id: 58, page_number: 1, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: 'Latency is propagation delay + transmission delay. Throughput is bits per second. Jitter is packet delay variation.',
      verified_text: 'Latency is propagation delay + transmission delay. Throughput is bits per second. Jitter is packet delay variation.',
      confidence: 0.95,
      review_required: false,
      verified: true,
    },
    ai: {
      status: 'done',
      latest: {
        id: 943,
        answer_id: 815,
        mode_requested: 'standard',
        mode_used: 'standard',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 4.5,
        max_marks: 5,
        confidence: 0.93,
        llm_confidence: 0.95,
        criteria: [
          { criterion_id: 'c1', criterion: 'Latency definition', max_marks: 2, awarded_marks: 2, reason: 'Includes delay components.' },
          { criterion_id: 'c2', criterion: 'Throughput definition', max_marks: 2, awarded_marks: 1.5, reason: 'Identifies bits per second.' },
          { criterion_id: 'c3', criterion: 'Jitter definition', max_marks: 1, awarded_marks: 1, reason: 'Identifies packet delay variation.' },
        ],
        overall_reason: 'Accurate technical answer.',
        warnings: [],
        stale: false,
        created_at: '2026-09-19T09:45:00Z',
      },
    },
    evaluation: {
      id: 703,
      marks_awarded: 4.5,
      criterion_marks: { c1: 2, c2: 1.5, c3: 1 },
      comment: 'Accepted AI recommendation.',
      source: 'ai_accepted',
      status: 'submitted',
      submitted_at: '2026-09-19T09:48:00Z',
      examiner: { id: 2, full_name: 'Dr. Alan Turing' },
    },
    marking_status: 'marked',
    final_marks: 4.5,
    final_source: 'examiner',
    navigation: {
      position: 5,
      total: 6,
      prev_answer_id: 814,
      next_answer_id: 816,
    },
    student: INITIAL_STUDENTS[3],
  },

  // Answer 816: S-0420, Q2 (Moderated)
  {
    id: 816,
    exam_id: 1,
    anon_code: 'S-0420',
    question: {
      id: 22,
      question_number: '2',
      text: 'Explain the TCP three-way handshake with a state diagram and the role of each segment.',
      max_marks: 10,
      evaluation_mode: 'standard',
    },
    rubric: INITIAL_QUESTIONS[1].rubric!,
    pages: [{ id: 59, page_number: 2, image_url: SAMPLE_PAGE_SVG }],
    is_attempted: true,
    ocr: {
      status: 'done',
      text: 'Three way handshake: 1. SYN 2. SYN-ACK 3. ACK. Diagrams and sequences fully annotated.',
      verified_text: 'Three way handshake: 1. SYN 2. SYN-ACK 3. ACK. Diagrams and sequences fully annotated.',
      confidence: 0.91,
      review_required: false,
      verified: true,
    },
    ai: {
      status: 'done',
      latest: {
        id: 944,
        answer_id: 816,
        mode_requested: 'standard',
        mode_used: 'standard',
        model_name: 'gemini-1.5-pro',
        prompt_version: 'v1.0',
        suggested_marks: 9.0,
        max_marks: 10,
        confidence: 0.90,
        llm_confidence: 0.92,
        criteria: [
          { criterion_id: 'c1', criterion: 'SYN segment', max_marks: 2, awarded_marks: 2, reason: 'Correct.' },
          { criterion_id: 'c2', criterion: 'SYN-ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Correct.' },
          { criterion_id: 'c3', criterion: 'ACK segment', max_marks: 2, awarded_marks: 2, reason: 'Correct.' },
          { criterion_id: 'c4', criterion: 'Purpose & Sequence Numbers', max_marks: 2, awarded_marks: 1.5, reason: 'Good.' },
          { criterion_id: 'c5', criterion: 'Diagram & Overall correctness', max_marks: 2, awarded_marks: 1.5, reason: 'Good diagram.' },
        ],
        overall_reason: 'Well rounded answer.',
        warnings: [],
        stale: false,
        created_at: '2026-09-19T09:50:00Z',
      },
    },
    evaluation: {
      id: 704,
      marks_awarded: 6.0,
      criterion_marks: { c1: 1, c2: 1, c3: 1, c4: 1.5, c5: 1.5 },
      comment: 'Under-marked by examiner initially.',
      source: 'ai_modified',
      status: 'submitted',
      submitted_at: '2026-09-19T09:52:00Z',
      examiner: { id: 2, full_name: 'Dr. Alan Turing' },
    },
    moderation: {
      id: 401,
      answer_id: 816,
      decision: 'overridden',
      moderated_marks: 8.5,
      reason: 'Diagram is complete and state transitions accurately match standard specification.',
      moderator: { id: 3, full_name: 'Dean Grace Hopper' },
      created_at: '2026-09-19T10:15:00Z',
    },
    marking_status: 'moderated',
    final_marks: 8.5,
    final_source: 'moderator',
    navigation: {
      position: 6,
      total: 6,
      prev_answer_id: 815,
      next_answer_id: null,
    },
    student: INITIAL_STUDENTS[3],
  },
]

export const INITIAL_ANOMALIES: Anomaly[] = [
  {
    id: 301,
    exam_id: 1,
    type: 'AI_DISAGREEMENT',
    severity: 'high',
    answer_id: 814,
    question_id: 22,
    examiner_id: 2,
    score: 6.5,
    details: {
      examiner_marks: 2.0,
      ai_marks: 8.5,
      difference: 6.5,
      ratio: 0.65,
    },
    status: 'open',
    note: 'Examiner awarded 2.0 while AI suggested 8.5 on verified high-confidence text.',
    detected_at: '2026-09-19T10:00:00Z',
  },
  {
    id: 302,
    exam_id: 1,
    type: 'UNCHECKED_ANSWER',
    severity: 'high',
    answer_id: 812,
    question_id: 22,
    examiner_id: 2,
    score: 0,
    details: {
      note: 'Attempted answer has not received submitted marks and exam is moving toward moderation.',
    },
    status: 'open',
    note: 'Pending examiner marking.',
    detected_at: '2026-09-19T10:05:00Z',
  },
  {
    id: 303,
    exam_id: 1,
    type: 'EXAMINER_DEVIATION',
    severity: 'medium',
    answer_id: 814,
    question_id: 22,
    examiner_id: 2,
    score: 2.1,
    details: {
      examiner_mean: 4.2,
      global_mean: 7.1,
      z_score: 2.1,
    },
    status: 'open',
    note: 'Examiner mean is notably below question benchmark.',
    detected_at: '2026-09-19T10:10:00Z',
  },
]

export const INITIAL_PROCESSING_STATUS: ProcessingStatus = {
  ocr: { pending: 0, processing: 0, done: 12, failed: 0 },
  ai: { not_requested: 0, pending: 0, processing: 0, done: 11, failed: 0 },
  review_required: 1,
  marking: { pending: 2, marked: 8, flagged: 1, moderated: 1 },
}

export const INITIAL_ANALYTICS_OVERVIEW: AnalyticsOverview = {
  answers_total: 12,
  ocr_done: 12,
  ai_done: 11,
  marked: 9,
  flagged: 1,
  moderated: 1,
  unchecked: 1,
  low_ocr_confidence: 1,
  avg_seconds_per_answer: 42.5,
}

export const INITIAL_EXAMINER_ANALYTICS: ExaminerAnalytics[] = [
  {
    examiner: { id: 2, full_name: 'Dr. Alan Turing' },
    marked: 9,
    mean: 7.2,
    sd: 1.8,
    mean_vs_global: -0.4,
    avg_seconds: 42.5,
    pct_ai_accepted: 66.7,
    pct_ai_modified: 22.2,
    pct_manual: 11.1,
    flags: 2,
  },
]

export const INITIAL_QUESTION_ANALYTICS: QuestionAnalytics[] = [
  {
    question_id: 21,
    question_number: '1',
    mean: 4.6,
    sd: 0.4,
    min: 4.0,
    max: 5.0,
    histogram: [
      { bucket: '0 - 1', count: 0 },
      { bucket: '1 - 2', count: 0 },
      { bucket: '2 - 3', count: 0 },
      { bucket: '3 - 4', count: 1 },
      { bucket: '4 - 5', count: 3 },
    ],
  },
  {
    question_id: 22,
    question_number: '2',
    mean: 6.8,
    sd: 2.6,
    min: 2.0,
    max: 9.5,
    histogram: [
      { bucket: '0 - 2', count: 1 },
      { bucket: '2 - 4', count: 0 },
      { bucket: '4 - 6', count: 1 },
      { bucket: '6 - 8', count: 1 },
      { bucket: '8 - 10', count: 2 },
    ],
  },
  {
    question_id: 23,
    question_number: '3',
    mean: 12.8,
    sd: 1.5,
    min: 10.0,
    max: 14.5,
    histogram: [
      { bucket: '0 - 3', count: 0 },
      { bucket: '3 - 6', count: 0 },
      { bucket: '6 - 9', count: 0 },
      { bucket: '9 - 12', count: 1 },
      { bucket: '12 - 15', count: 3 },
    ],
  },
]

export const INITIAL_RESULTS: ExamResults = {
  items: [
    {
      id: 1,
      student: INITIAL_STUDENTS[0],
      total_marks: 25.0,
      max_marks: 30.0,
      percentage: 83.3,
      status: 'draft',
    },
    {
      id: 2,
      student: INITIAL_STUDENTS[1],
      total_marks: 27.5,
      max_marks: 30.0,
      percentage: 91.7,
      status: 'draft',
    },
    {
      id: 3,
      student: INITIAL_STUDENTS[2],
      total_marks: 18.0,
      max_marks: 30.0,
      percentage: 60.0,
      status: 'draft',
    },
    {
      id: 4,
      student: INITIAL_STUDENTS[3],
      total_marks: 24.5,
      max_marks: 30.0,
      percentage: 81.7,
      status: 'draft',
    },
  ],
  stats: {
    mean: 23.75,
    median: 24.75,
    pass_rate: 100.0,
    min: 18.0,
    max: 27.5,
  },
}
