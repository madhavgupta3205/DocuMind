import { useState, useRef, useEffect } from "react";
import axios from "axios";
import DocumentManager from "./DocumentManager";

export default function Chat({ token, user, onLogout }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showDocManager, setShowDocManager] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("all");
  const [showDocSelector, setShowDocSelector] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Fetch user documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(
        "http://localhost:8000/api/v1/documents/list",
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
      await axios.post(
        "http://localhost:8000/api/v1/documents/upload",
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

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userMessage = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setQuery("");
    setLoading(true);

    try {
      // Build query with optional doc filter
      const queryPayload = { query };
      if (selectedDocId !== "all") {
        queryPayload.doc_id = selectedDocId;
      }

      const response = await fetch("http://localhost:8000/api/v1/chat/query", {
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
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">DocuMind AI</h1>
            <p className="text-sm text-gray-600">{user?.email}</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setShowDocManager(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
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
            <label className="cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
              {uploading ? "Uploading..." : "Upload Document"}
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt"
                className="hidden"
                disabled={uploading}
              />
            </label>
            <button
              onClick={onLogout}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Logout
            </button>
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                Welcome to DocuMind AI
              </h2>
              <p className="text-gray-600">
                Upload documents and ask questions about them
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-lg ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-white text-gray-900 shadow-sm border"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
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
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Sending..." : "Send"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
