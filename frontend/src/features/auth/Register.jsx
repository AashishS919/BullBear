import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from './AuthLayout'
import { Field, Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { useAuth } from '../../context/AuthContext'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
// Strict: min 8 chars, one upper, one lower, one digit.
const PW_RE = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/

export function Register() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [busy, setBusy] = useState(false)

  function validate() {
    const e = {}
    if (form.name.trim().length < 3) e.name = 'Full name must be at least 3 characters.'
    if (!EMAIL_RE.test(form.email)) e.email = 'Enter a valid email address.'
    if (!PW_RE.test(form.password)) e.password = 'Min 8 chars with upper, lower, and a number.'
    if (form.confirm !== form.password) e.confirm = 'Passwords do not match.'
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
      await register({ name: form.name.trim(), email: form.email, password: form.password })
      navigate('/', { replace: true })
    } catch (err) {
      setSubmitError(err.message || 'Registration failed.')
    } finally {
      setBusy(false)
    }
  }

  const set = (k) => (ev) => setForm((f) => ({ ...f, [k]: ev.target.value }))

  return (
    <AuthLayout
      title="Create account"
      subtitle="Start trading on the simulated NEPSE environment"
      footer={<>Already registered? <Link to="/login" className="font-medium text-accent hover:underline">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {submitError && (
          <div className="rounded-md border border-bear/30 bg-bear-soft px-3 py-2 text-sm text-bear">
            {submitError}
          </div>
        )}
        <Field label="Full Name" htmlFor="name" required error={errors.name}>
          <Input id="name" autoComplete="name" placeholder="Enter your full name"
            value={form.name} onChange={set('name')} invalid={!!errors.name} />
        </Field>
        <Field label="Email" htmlFor="email" required error={errors.email}>
          <Input id="email" type="email" autoComplete="email" placeholder="Enter your email"
            value={form.email} onChange={set('email')} invalid={!!errors.email} />
        </Field>
        <Field label="Password" htmlFor="password" required error={errors.password}
          hint="At least 8 characters, with uppercase, lowercase, and a number.">
          <Input id="password" type="password" autoComplete="new-password" placeholder="********"
            value={form.password} onChange={set('password')} invalid={!!errors.password} />
        </Field>
        <Field label="Confirm Password" htmlFor="confirm" required error={errors.confirm}>
          <Input id="confirm" type="password" autoComplete="new-password" placeholder="********"
            value={form.confirm} onChange={set('confirm')} invalid={!!errors.confirm} />
        </Field>
        <Button type="submit" size="lg" className="w-full" disabled={busy}>
          {busy ? 'Creating...' : 'Create Account'}
        </Button>
      </form>
    </AuthLayout>
  )
}
