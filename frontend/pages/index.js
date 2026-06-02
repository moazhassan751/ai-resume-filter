import Link from 'next/link'
import Head from 'next/head'

export default function Home() {
  return (
    <>
      <Head>
        <title>TalentLens AI — Recruitment Intelligence</title>
      </Head>

      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #050912; color: #f0f4ff; font-family: 'DM Sans', sans-serif; }
        .hero { min-height: 100vh; display: flex; flex-direction: column; }
        nav { display: flex; justify-content: space-between; align-items: center; padding: 24px 48px; border-bottom: 1px solid #0f1a30; }
        .logo { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 20px; color: #10b981; letter-spacing: -0.5px; }
        .nav-links { display: flex; gap: 32px; align-items: center; }
        .nav-links a { color: #9ca3af; text-decoration: none; font-size: 14px; transition: color .2s; }
        .nav-links a:hover { color: #f0f4ff; }
        .btn-primary { background: #10b981; color: #050912; padding: 10px 24px; border-radius: 8px; font-weight: 500; text-decoration: none; font-size: 14px; transition: opacity .2s; }
        .btn-primary:hover { opacity: .85; }
        .main { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; text-align: center; position: relative; overflow: hidden; }
        .glow { position: absolute; width: 600px; height: 600px; border-radius: 50%; background: radial-gradient(circle, rgba(16,185,129,.15) 0%, transparent 70%); top: 50%; left: 50%; transform: translate(-50%, -55%); pointer-events: none; }
        .badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); border-radius: 100px; padding: 6px 16px; font-size: 12px; color: #10b981; margin-bottom: 32px; letter-spacing: .04em; }
        .dot { width: 6px; height: 6px; border-radius: 50%; background: #10b981; animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
        h1 { font-family: 'Syne', sans-serif; font-size: clamp(42px, 7vw, 88px); font-weight: 800; line-height: 1.05; letter-spacing: -2px; max-width: 900px; margin-bottom: 24px; }
        h1 span { color: #10b981; }
        .subtitle { font-size: 18px; color: #6b7280; max-width: 560px; line-height: 1.7; margin-bottom: 48px; font-weight: 300; }
        .cta-group { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; }
        .btn-outline { border: 1px solid #1f2937; color: #9ca3af; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-size: 14px; transition: all .2s; }
        .btn-outline:hover { border-color: #374151; color: #f0f4ff; }
        .btn-hero { background: #10b981; color: #050912; padding: 14px 32px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 15px; transition: all .2s; box-shadow: 0 0 40px rgba(16,185,129,.3); }
        .btn-hero:hover { box-shadow: 0 0 60px rgba(16,185,129,.5); transform: translateY(-1px); }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 24px; padding: 80px 48px; max-width: 1200px; margin: 0 auto; width: 100%; }
        .card { background: #0a0f1e; border: 1px solid #0f1a30; border-radius: 16px; padding: 32px; transition: border-color .2s; }
        .card:hover { border-color: rgba(16,185,129,.3); }
        .card-icon { font-size: 28px; margin-bottom: 16px; }
        .card h3 { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 700; margin-bottom: 10px; }
        .card p { color: #6b7280; font-size: 14px; line-height: 1.7; }
        footer { text-align: center; padding: 32px; border-top: 1px solid #0f1a30; color: #374151; font-size: 13px; }
      `}</style>

      <div className="hero">
        <nav>
          <div className="logo">TalentLens AI</div>
          <div className="nav-links">
            <Link href="/analytics">Analytics</Link>
            <Link href="/upload">Upload</Link>
            <Link href="/history">History</Link>
            <Link href="/dashboard">Dashboard</Link>
            <Link href="/login">Sign in</Link>
            <Link href="/signup" className="btn-primary">Get started</Link>
          </div>
        </nav>

        <div className="main">
          <div className="glow" />
          <div className="badge">
            <span className="dot" />
            Agentic Recruitment Intelligence
          </div>
          <h1>Hire smarter with <span>AI-powered</span> resume intelligence</h1>
          <p className="subtitle">
            Classify, score, and semantically search thousands of resumes in seconds.
            Built on a multi-dataset ML pipeline with explainable predictions.
          </p>
          <div className="cta-group">
            <Link href="/signup" className="btn-hero">Start for free →</Link>
            <Link href="/dashboard" className="btn-outline">View dashboard</Link>
          </div>
        </div>

        <div className="features">
          {[
            { icon: '🧠', title: 'Resume Classification', desc: 'TF-IDF + Logistic Regression trained on 30k+ labelled resumes across 24 job categories.' },
            { icon: '🔍', title: 'Semantic Search', desc: 'Sentence-transformer embeddings indexed in ChromaDB for cosine-similarity candidate retrieval.' },
            { icon: '📊', title: 'ATS Scoring Engine', desc: 'Skill overlap detection, missing keyword analysis, and a 0–100 ATS fitness score.' },
            { icon: '🤖', title: 'Multi-Agent AI', desc: 'CrewAI agents for resume analysis, skill gap detection, bias flagging, and hiring recommendations.' },
            { icon: '📈', title: 'Analytics Dashboard', desc: 'Accuracy, F1, confusion matrix, category distribution, and hiring funnel visualisations.' },
            { icon: '🔐', title: 'Secure & Scalable', desc: 'JWT OAuth2 auth, MongoDB persistence, and async FastAPI backend built for production.' },
          ].map((f, i) => (
            <div key={i} className="card">
              <div className="card-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>

        <footer>© {new Date().getFullYear()} TalentLens AI — Built with FastAPI + Next.js</footer>
      </div>
    </>
  )
}