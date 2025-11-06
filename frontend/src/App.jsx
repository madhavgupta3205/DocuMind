import { useState } from 'react'
import Login from './components/Login'
import Chat from './components/Chat'
import './App.css'

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)

  const handleLogin = (authToken, userData) => {
    localStorage.setItem('token', authToken)
    setToken(authToken)
    setUser(userData)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {!token ? (
        <Login onLogin={handleLogin} />
      ) : (
        <Chat token={token} user={user} onLogout={handleLogout} />
      )}
    </div>
  )
}

export default App
