import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from './AuthLayout'
import { Field, Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { useAuth } from '../../context/AuthContext'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [busy, setBusy] = useState(false)

  function validate() {
    const e = {}
    if (!EMAIL_RE.test(form.email)) e.email = 'Enter a valid email address.'
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters.'
    return e
  }

  async function submit(ev) {
    ev.preventDefault()
    setSubmitError('')
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    try {
      await login(form.email, form.password)
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      setSubmitError(err.message || 'Login failed.')
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (ev) => setForm((f) => ({ ...f, [k]: ev.target.value }))

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your BullBear account"
      footer={<>No account? <Link to="/register" className="font-medium text-accent hover:underline">Create one</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {submitError && (
          <div className="rounded-md border border-bear/30 bg-bear-soft px-3 py-2 text-sm text-bear">
            {submitError}
          </div>
        )}
        <Field label="Email" htmlFor="email" required error={errors.email}>
          <Input id="email" type="email" autoComplete="email" placeholder="you@example.com"
            value={form.email} onChange={set('email')} invalid={!!errors.email} />
        </Field>
        <Field label="Password" htmlFor="password" required error={errors.password}>
          <Input id="password" type="password" autoComplete="current-password" placeholder="********"
            value={form.password} onChange={set('password')} invalid={!!errors.password} />
        </Field>
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? 'Signing in...' : 'Sign In'}
        </Button>
        <p className="text-center text-xs text-ink-3">
          Demo admin: aashish@gmail.com / Admin@123
        </p>
      </form>
    </AuthLayout>
  )
}
