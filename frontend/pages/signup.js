import { useState } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import Head from 'next/head'
import { registerRequest } from '../src/lib/auth'

export default function SignupPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await registerRequest(email, password, name)
      router.push('/login')
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Head><title>Create Account — TalentLens AI</title></Head>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #050912; color: #f0f4ff; font-family: 'DM Sans', -apple-system, sans-serif; }
        .page { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; }
        .card { background: #0a0f1e; border: 1px solid #0f1a30; border-radius: 20px; padding: 48px 40px; width: 100%; max-width: 420px; }
        .logo { font-size: 22px; font-weight: 800; color: #10b981; margin-bottom: 32px; letter-spacing: -0.5px; }
        h2 { font-size: 24px; font-weight: 700; margin-bottom: 6px; }
        .sub { color: #6b7280; font-size: 14px; margin-bottom: 32px; }
        label { display: block; font-size: 13px; color: #9ca3af; margin-bottom: 6px; }
        input { width: 100%; background: #0d1424; border: 1px solid #1f2937; border-radius: 10px; padding: 12px 14px; color: #f0f4ff; font-size: 14px; outline: none; transition: border-color .2s; margin-bottom: 20px; }
        input:focus { border-color: #10b981; }
        button { width: 100%; background: #10b981; color: #050912; border: none; border-radius: 10px; padding: 14px; font-size: 15px; font-weight: 600; cursor: pointer; transition: opacity .2s; margin-top: 8px; }
        button:hover { opacity: .88; }
        button:disabled { opacity: .5; cursor: not-allowed; }
        .error { background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); border-radius: 8px; color: #f87171; font-size: 13px; padding: 10px 14px; margin-bottom: 16px; }
        .footer { margin-top: 28px; text-align: center; font-size: 14px; color: #6b7280; }
        .footer a { color: #10b981; text-decoration: none; }
      `}</style>

      <div className="page">
        <div className="card">
          <div className="logo">TalentLens AI</div>
          <h2>Create your account</h2>
          <p className="sub">Start screening resumes intelligently</p>

          {error && <div className="error">{error}</div>}

          <form onSubmit={submit}>
            <label>Full name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder="Jane Smith" />
            <label>Email address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" required />
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Min. 8 characters" required minLength={8} />
            <button type="submit" disabled={loading}>
              {loading ? 'Creating account…' : 'Create account →'}
            </button>
          </form>

          <div className="footer">
            Already have an account? <Link href="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </>
  )
}