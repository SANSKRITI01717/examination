import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'

export const Login: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const { toast, errorToast } = useToast()

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setIsLoading(true)
    try {
      await login(email, password)
      toast('Logged in successfully', 'success')
      // Redirect based on role will happen or default to root
      navigate('/')
    } catch (err) {
      errorToast(err)
    } finally {
      setIsLoading(false)
    }
  }

  const quickLogin = async (demoEmail: string) => {
    setEmail(demoEmail)
    setPassword('demo-password')
    setIsLoading(true)
    try {
      await login(demoEmail, 'demo-password')
      toast(`Signed in as ${demoEmail}`, 'success')
      navigate('/')
    } catch (err) {
      errorToast(err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-12 h-12 rounded-xl bg-indigo-500 mx-auto flex items-center justify-center font-black text-white text-xl shadow-lg shadow-indigo-500/30">
          OSM
        </div>
        <h2 className="mt-4 text-2xl font-black tracking-tight text-white">
          Digital Examination & OSM
        </h2>
        <p className="mt-1 text-xs text-slate-400">
          AI-assisted On-Screen Marking Platform for Universities
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-100">
          <form className="space-y-4" onSubmit={handleLogin}>
            <Input
              label="Email Address"
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="name@univ.edu"
            />

            <Input
              label="Password"
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              isLoading={isLoading}
            >
              Sign In
            </Button>
          </form>

          {/* Quick Hackathon Demo Roles */}
          <div className="mt-6 pt-6 border-t border-slate-200 text-center">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              One-Click Demo Roles
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => quickLogin('admin@univ.edu')}
                className="px-2.5 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 transition-colors border border-slate-200 cursor-pointer"
              >
                Admin
              </button>
              <button
                type="button"
                onClick={() => quickLogin('examiner@univ.edu')}
                className="px-2.5 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 transition-colors border border-slate-200 cursor-pointer"
              >
                Examiner
              </button>
              <button
                type="button"
                onClick={() => quickLogin('moderator@univ.edu')}
                className="px-2.5 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-indigo-50 hover:text-indigo-600 text-slate-700 transition-colors border border-slate-200 cursor-pointer"
              >
                Moderator
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mt-3 italic">
              Role permissions strictly enforced per instruction.md
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
