import { useState } from "react";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email.trim() && password.trim()) {
      onLogin();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f172a] via-[#020617] to-black flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="mb-6 text-center text-white/70 text-xs tracking-[0.25em] uppercase">
           Municipal OS
        </div>

        <div className="glass-card bg-white/10 border-white/20 text-white p-8 rounded-3xl">
          <h1 className="text-2xl md:text-3xl font-semibold mb-2">
            Sign in to continue
          </h1>
          <p className="text-sm text-white/60 mb-8">
            Access the waste intelligence dashboard for your municipality.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-white/60 mb-1">
                Email
              </label>
              <input
                type="email"
                className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/15 text-sm outline-none focus:ring-2 focus:ring-blue-400/70 focus:border-transparent placeholder:text-white/30"
                placeholder="you@example.com"
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs text-white/60 mb-1">
                Password
              </label>
              <input
                type="password"
                className="w-full px-3 py-2.5 rounded-xl bg-white/5 border border-white/15 text-sm outline-none focus:ring-2 focus:ring-blue-400/70 focus:border-transparent placeholder:text-white/30"
                placeholder="••••••••"
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              className="w-full mt-2 py-2.5 rounded-xl bg-white text-black text-sm font-medium hover:bg-white/90 transition shadow-[0_14px_35px_rgba(0,0,0,0.35)]"
            >
              Continue
            </button>
          </form>

          <p className="mt-6 text-[11px] text-white/40 text-center">
            This is a demo build. Any email / password combination will sign
            you in.
          </p>
        </div>
      </div>
    </div>
  );
}
