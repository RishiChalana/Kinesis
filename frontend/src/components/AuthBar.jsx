import { useState } from "react";
import { isAuthed, login, logout } from "../api";

export default function AuthBar() {
  const [authed, setAuthed] = useState(isAuthed());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState(null);

  async function doLogin(e) {
    e.preventDefault();
    setErr(null);
    try {
      await login(email, password);
      setAuthed(true);
    } catch {
      setErr("Login failed");
    }
  }

  if (authed) {
    return (
      <span className="authbar">
        <span className="authed-dot" /> signed in
        <button className="link-btn" onClick={() => { logout(); setAuthed(false); }}>
          log out
        </button>
      </span>
    );
  }

  return (
    <form className="authbar" onSubmit={doLogin}>
      <input placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="password" type="password" value={password}
             onChange={(e) => setPassword(e.target.value)} />
      <button className="link-btn" type="submit">log in</button>
      {err && <span className="auth-err">{err}</span>}
    </form>
  );
}
