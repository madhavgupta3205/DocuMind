import { useState, useRef, useEffect } from "react";
import axios from "axios";
import DocumentManager from "./DocumentManager";
import Profile from "./Profile";

export default function Chat({ token, user, onLogout }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showDocManager, setShowDocManager] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("all");
  const [showDocSelector, setShowDocSelector] = useState(false);
  const [userProfile, setUserProfile] = useState(user);
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [showSidebar, setShowSidebar] = useState(window.innerWidth >= 768);
  const messagesEndRef = useRef(null);
  const profileMenuRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Fetch user documents and chat sessions on mount
  useEffect(() => {
    fetchDocuments();
    fetchUserProfile();
    fetchChatSessions();
  }, []);

  // Close profile menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target)
      ) {
        setShowProfileMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const fetchUserProfile = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await axios.get(`${API_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setUserProfile(response.data);
    } catch (err) {
      console.error("Failed to fetch user profile:", err);
    }
  };

  const handleProfileUpdate = (updatedProfile) => {
    setUserProfile(updatedProfile);
  };

  const fetchDocuments = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await axios.get(
        `${API_URL}/api/v1/documents/list`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setDocuments(response.data.documents || []);
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    }
  };

  const handleFileUpload = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      await axios.post(
        `${API_URL}/api/v1/documents/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        }
      );
      alert("Document uploaded successfully!");
      setFile(null);
      // Refresh document list
      await fetchDocuments();
    } catch (error) {
      alert(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const fetchChatSessions = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await axios.get(
        `${API_URL}/api/v1/chat/sessions`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setChatSessions(response.data.sessions || []);
    } catch (error) {
      console.error("Failed to fetch chat sessions:", error);
    }
  };

  const createNewChat = async () => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await axios.post(
        `${API_URL}/api/v1/chat/sessions`,
        { title: "New Chat" },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const newSession = response.data;
      setChatSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
    } catch (error) {
      console.error("Failed to create chat session:", error);
    }
  };

  const loadChatSession = async (sessionId) => {
    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await axios.get(
        `${API_URL}/api/v1/chat/sessions/${sessionId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setCurrentSessionId(sessionId);
      setMessages(response.data.messages || []);
      // Close sidebar on mobile after selecting a chat
      if (window.innerWidth < 768) {
        setShowSidebar(false);
      }
    } catch (error) {
      console.error("Failed to load chat session:", error);
    }
  };

  const deleteChatSession = async (sessionId) => {
    if (!confirm("Are you sure you want to delete this chat?")) return;

    try {
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      await axios.delete(
        `${API_URL}/api/v1/chat/sessions/${sessionId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setChatSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error("Failed to delete chat session:", error);
      alert("Failed to delete chat session");
    }
  };

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    // Create new session if none exists
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
        const response = await axios.post(
          `${API_URL}/api/v1/chat/sessions`,
          { title: "New Chat" },
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        const newSession = response.data;
        setChatSessions((prev) => [newSession, ...prev]);
        setCurrentSessionId(newSession.id);
        sessionId = newSession.id;
      } catch (error) {
        console.error("Failed to create chat session:", error);
      }
    }

    const userMessage = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      // Build query with optional doc filter and session_id
      const queryPayload = {
        query,
        session_id: sessionId,
      };
      if (selectedDocId !== "all") {
        queryPayload.doc_id = selectedDocId;
      }

      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_URL}/api/v1/chat/query`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(queryPayload),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiResponse = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));

            if (data.type === "token") {
              aiResponse += data.content;
              setMessages((prev) => {
                const newMessages = [...prev];
                if (newMessages[newMessages.length - 1]?.role === "assistant") {
                  newMessages[newMessages.length - 1].content = aiResponse;
                } else {
                  newMessages.push({ role: "assistant", content: aiResponse });
                }
                return newMessages;
              });
            }
          }
        }
      }

      // Update session title with first query if it's a new chat
      if (sessionId && messages.length === 0) {
        const title =
          query.length > 50 ? query.substring(0, 50) + "..." : query;
        setChatSessions((prev) =>
          prev.map((s) => ((s.id || s._id) === sessionId ? { ...s, title } : s))
        );
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: Could not process query",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-linear-to-br from-gray-50 via-blue-50 to-indigo-50">
      {/* Mobile Backdrop */}
      {showSidebar && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setShowSidebar(false)}
        ></div>
      )}

      {/* Sidebar */}
      <div
        className={`${showSidebar ? "w-72" : "w-0"} md:${
          showSidebar ? "w-72" : "w-0"
        } transition-all duration-300 overflow-hidden bg-white/80 backdrop-blur-lg border-r border-gray-200/50 flex flex-col fixed md:relative inset-y-0 left-0 z-40 ${
          showSidebar ? "shadow-2xl" : ""
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-gray-200/50">
          <button
            onClick={createNewChat}
            className="w-full px-4 py-3 bg-linear-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200 font-semibold flex items-center justify-center gap-2"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 4v16m8-8H4"
              />
            </svg>
            New Chat
          </button>
        </div>

        {/* Chat Sessions List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {chatSessions.map((session) => (
            <div
              key={session.id || session._id}
              className={`group relative p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                currentSessionId === (session.id || session._id)
                  ? "bg-indigo-50 border-2 border-indigo-200"
                  : "bg-white/50 hover:bg-white border border-gray-200 hover:border-indigo-200"
              }`}
              onClick={() => loadChatSession(session.id || session._id)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <svg
                      className="h-4 w-4 text-gray-500 shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                      />
                    </svg>
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {session.title || "New Chat"}
                    </p>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(session.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteChatSession(session.id || session._id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all duration-200"
                  title="Delete chat"
                >
                  <svg
                    className="h-4 w-4 text-red-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))}
          {chatSessions.length === 0 && (
            <div className="text-center py-8 text-gray-500 text-sm">
              <p>No chat history yet.</p>
              <p className="mt-1">Start a new chat!</p>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white/80 backdrop-blur-lg shadow-lg border-b border-gray-200/50 px-6 py-4">
          <div className="max-w-5xl mx-auto flex justify-between items-center">
            <div className="flex items-center gap-3">
              {/* Sidebar Toggle */}
              <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title={showSidebar ? "Hide sidebar" : "Show sidebar"}
              >
                <svg
                  className="h-6 w-6 text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
              <div className="w-10 h-10 bg-linear-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-linear-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  DocuMind AI
                </h1>
                <p className="text-xs text-gray-500 font-medium">
                  {userProfile?.email || user?.email}
                </p>
              </div>
            </div>
            <div className="flex gap-2 items-center">
              <button
                onClick={() => setShowDocManager(true)}
                className="px-4 py-2.5 bg-linear-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200 flex items-center gap-2 font-medium"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                Manage Documents
              </button>
              <label className="cursor-pointer bg-linear-to-r from-blue-600 to-cyan-600 text-white px-4 py-2.5 rounded-xl hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200 font-medium flex items-center gap-2">
                {uploading ? (
                  <>
                    <svg
                      className="animate-spin h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Uploading...
                  </>
                ) : (
                  <>
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                    Upload
                  </>
                )}
                <input
                  type="file"
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  disabled={uploading}
                />
              </label>

              {/* Profile Dropdown */}
              <div className="relative" ref={profileMenuRef}>
                <button
                  onClick={() => setShowProfileMenu(!showProfileMenu)}
                  className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-xl hover:bg-white hover:shadow-md transition-all duration-200"
                >
                  <div className="w-8 h-8 bg-linear-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-md">
                    {(userProfile?.email || user?.email)
                      ?.charAt(0)
                      .toUpperCase() || "U"}
                  </div>
                  <svg
                    className={`h-4 w-4 text-gray-600 transition-transform ${
                      showProfileMenu ? "rotate-180" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Dropdown Menu */}
                {showProfileMenu && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900">
                        {userProfile?.full_name || "User"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {userProfile?.email || user?.email}
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        setShowProfile(true);
                        setShowProfileMenu(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-3"
                    >
                      <svg
                        className="h-5 w-5 text-gray-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                        />
                      </svg>
                      Profile Settings
                    </button>

                    <button
                      onClick={() => {
                        onLogout();
                        setShowProfileMenu(false);
                      }}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-3"
                    >
                      <svg
                        className="h-5 w-5 text-red-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                        />
                      </svg>
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Document Manager Modal */}
        {showDocManager && (
          <DocumentManager
            onClose={() => setShowDocManager(false)}
            onDocumentsChange={(docs) => setDocuments(docs)}
          />
        )}

        {/* Profile Modal */}
        {showProfile && (
          <Profile
            token={token}
            onClose={() => setShowProfile(false)}
            onProfileUpdate={handleProfileUpdate}
          />
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 ? (
              <div className="text-center py-20 animate-fade-in-up">
                <div className="inline-flex items-center justify-center w-20 h-20 bg-linear-to-br from-indigo-100 to-purple-100 rounded-3xl mb-6 animate-bounce-subtle">
                  <svg
                    className="w-10 h-10 text-indigo-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-gray-800 mb-3">
                  Welcome to DocuMind AI
                </h2>
                <p className="text-gray-600 mb-8 max-w-md mx-auto">
                  Upload your documents and start asking intelligent questions.
                  Our AI will analyze and provide accurate answers.
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  <div className="bg-white/80 backdrop-blur-sm border border-gray-200 rounded-xl px-4 py-3 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center gap-2 text-sm">
                      <svg
                        className="w-5 h-5 text-purple-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"
                        />
                      </svg>
                      <span className="text-gray-700 font-medium">
                        PDF Support
                      </span>
                    </div>
                  </div>
                  <div className="bg-white/80 backdrop-blur-sm border border-gray-200 rounded-xl px-4 py-3 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center gap-2 text-sm">
                      <svg
                        className="w-5 h-5 text-blue-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                      <span className="text-gray-700 font-medium">
                        Fast Answers
                      </span>
                    </div>
                  </div>
                  <div className="bg-white/80 backdrop-blur-sm border border-gray-200 rounded-xl px-4 py-3 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-center gap-2 text-sm">
                      <svg
                        className="w-5 h-5 text-cyan-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                        />
                      </svg>
                      <span className="text-gray-700 font-medium">
                        Secure & Private
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex animate-fade-in-up ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 bg-linear-to-br from-indigo-600 to-purple-600 rounded-full flex items-center justify-center shrink-0 mr-3 shadow-md">
                      <svg
                        className="w-5 h-5 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                        />
                      </svg>
                    </div>
                  )}
                  <div
                    className={`max-w-[75%] px-5 py-3.5 rounded-2xl shadow-sm ${
                      msg.role === "user"
                        ? "bg-linear-to-br from-indigo-600 to-purple-600 text-white"
                        : "bg-white text-gray-900 border border-gray-200"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {msg.content}
                    </p>
                  </div>
                  {msg.role === "user" && (
                    <div className="w-8 h-8 bg-linear-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center shrink-0 ml-3 shadow-md">
                      <svg
                        className="w-5 h-5 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                        />
                      </svg>
                    </div>
                  )}
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="bg-white/80 backdrop-blur-lg border-t border-gray-200/50 px-6 py-5 shadow-lg">
          <form onSubmit={handleQuery} className="max-w-3xl mx-auto">
            {/* Document Selector - Shows if user has documents */}
            {documents.length > 0 && (
              <div className="mb-3 flex items-center gap-2 text-sm">
                <span className="text-gray-600 font-medium">Query from:</span>
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowDocSelector(!showDocSelector)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                  >
                    <svg
                      className="h-4 w-4 text-gray-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span className="text-gray-700">
                      {selectedDocId === "all"
                        ? `All Documents (${documents.length})`
                        : documents.find((d) => d.doc_id === selectedDocId)
                            ?.filename || "Select Document"}
                    </span>
                    <svg
                      className={`h-4 w-4 text-gray-600 transition-transform ${
                        showDocSelector ? "rotate-180" : ""
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>

                  {/* Dropdown Menu */}
                  {showDocSelector && (
                    <div className="absolute bottom-full mb-2 left-0 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-[300px] max-h-[300px] overflow-y-auto">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedDocId("all");
                          setShowDocSelector(false);
                        }}
                        className={`w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center gap-2 ${
                          selectedDocId === "all"
                            ? "bg-blue-50 text-blue-700 font-medium"
                            : "text-gray-700"
                        }`}
                      >
                        <svg
                          className="h-5 w-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                          />
                        </svg>
                        <div>
                          <div>All Documents</div>
                          <div className="text-xs text-gray-500">
                            Search across {documents.length} document
                            {documents.length !== 1 ? "s" : ""}
                          </div>
                        </div>
                        {selectedDocId === "all" && (
                          <svg
                            className="ml-auto h-5 w-5 text-blue-700"
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path
                              fillRule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                        )}
                      </button>

                      <div className="border-t border-gray-200"></div>

                      {documents.map((doc) => (
                        <button
                          key={doc.doc_id}
                          type="button"
                          onClick={() => {
                            setSelectedDocId(doc.doc_id);
                            setShowDocSelector(false);
                          }}
                          className={`w-full text-left px-4 py-2.5 hover:bg-blue-50 transition-colors flex items-center gap-2 ${
                            selectedDocId === doc.doc_id
                              ? "bg-blue-50 text-blue-700 font-medium"
                              : "text-gray-700"
                          }`}
                        >
                          <svg
                            className="h-5 w-5 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          <div className="flex-1 min-w-0">
                            <div className="truncate">{doc.filename}</div>
                            <div className="text-xs text-gray-500">
                              {doc.chunk_count} chunks
                            </div>
                          </div>
                          {selectedDocId === doc.doc_id && (
                            <svg
                              className="h-5 w-5 text-blue-700 flex-shrink-0"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path
                                fillRule="evenodd"
                                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                clipRule="evenodd"
                              />
                            </svg>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {selectedDocId !== "all" && (
                  <button
                    type="button"
                    onClick={() => setSelectedDocId("all")}
                    className="text-blue-600 hover:text-blue-700 text-xs underline"
                  >
                    Clear filter
                  </button>
                )}
              </div>
            )}

            <div className="flex gap-3">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  selectedDocId === "all"
                    ? "Ask a question about your documents..."
                    : `Ask about ${
                        documents.find((d) => d.doc_id === selectedDocId)
                          ?.filename || "this document"
                      }...`
                }
                disabled={loading}
                className="flex-1 px-5 py-3.5 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:bg-gray-50 transition-all duration-200 text-gray-900 placeholder-gray-400"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="px-8 py-3.5 bg-linear-to-r from-indigo-600 to-purple-600 text-white rounded-xl hover:shadow-lg hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-200 font-semibold flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <svg
                      className="animate-spin h-5 w-5"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Sending...
                  </>
                ) : (
                  <>
                    Send
                    <svg
                      className="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                      />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
