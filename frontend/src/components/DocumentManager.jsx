import { useState, useEffect } from "react";
import axios from "axios";

function DocumentManager({ onClose, onDocumentsChange }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError("");
      const token = localStorage.getItem("token");

      const response = await axios.get(`${API_URL}/api/v1/documents/list`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const docs = response.data.documents || [];
      setDocuments(docs);
      // Notify parent component about document changes
      if (onDocumentsChange) {
        onDocumentsChange(docs);
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      setError("Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Check file type
      const validTypes = [
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ];
      if (!validTypes.includes(file.type) && !file.name.endsWith(".txt")) {
        setError("Invalid file type. Please upload PDF, TXT, or DOCX files.");
        return;
      }

      // Check file size (50MB limit)
      if (file.size > 52428800) {
        setError("File too large. Maximum size is 50MB.");
        return;
      }

      setSelectedFile(file);
      setError("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError("Please select a file first");
      return;
    }

    try {
      setUploading(true);
      setError("");
      setSuccess("");

      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await axios.post(
        `${API_URL}/api/v1/documents/upload`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setSuccess(
        `Successfully uploaded ${response.data.filename} (${response.data.chunks_created} chunks created)`
      );
      setSelectedFile(null);

      // Reset file input
      const fileInput = document.getElementById("file-input");
      if (fileInput) fileInput.value = "";

      // Refresh document list
      await fetchDocuments();
    } catch (err) {
      console.error("Upload failed:", err);
      setError(err.response?.data?.detail || "Failed to upload document");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (
      !confirm(
        `Are you sure you want to delete "${filename}"? This will remove all associated chunks and cannot be undone.`
      )
    ) {
      return;
    }

    try {
      setError("");
      setSuccess("");
      const token = localStorage.getItem("token");

      await axios.delete(`${API_URL}/api/v1/documents/documents/${docId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setSuccess(`Successfully deleted ${filename}`);

      // Refresh document list
      await fetchDocuments();
    } catch (err) {
      console.error("Delete failed:", err);
      setError(err.response?.data?.detail || "Failed to delete document");
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "Unknown";
    const date = new Date(isoString);
    return (
      date.toLocaleDateString() +
      " " +
      date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-800">
            Document Management
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Upload Section */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">
            Upload New Document
          </h3>

          <div className="flex gap-3 items-start">
            <div className="flex-1">
              <input
                id="file-input"
                type="file"
                onChange={handleFileSelect}
                accept=".pdf,.txt,.docx"
                className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {selectedFile && (
                <p className="text-sm text-gray-600 mt-2">
                  Selected: {selectedFile.name} (
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
            </div>

            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>

          {/* Messages */}
          {error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm">
              {success}
            </div>
          )}
        </div>

        {/* Documents List */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <h3 className="text-lg font-semibold text-gray-700 mb-3">
            Your Documents ({documents.length})
          </h3>

          {loading ? (
            <div className="text-center py-12 text-gray-500">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-3"></div>
              Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <svg
                className="mx-auto h-12 w-12 text-gray-400 mb-3"
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
              <p className="text-lg font-medium">No documents yet</p>
              <p className="text-sm mt-1">
                Upload your first document to get started
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800 text-lg flex items-center gap-2">
                        <svg
                          className="h-5 w-5 text-blue-600"
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
                        {doc.filename}
                      </h4>

                      <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Uploaded:</span>{" "}
                          {formatDate(doc.upload_date)}
                        </div>
                        <div>
                          <span className="font-medium">Chunks:</span>{" "}
                          {doc.chunk_count}
                        </div>
                        <div className="col-span-2">
                          <span className="font-medium">Doc ID:</span>{" "}
                          <code className="text-xs bg-gray-100 px-1 rounded">
                            {doc.doc_id}
                          </code>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDelete(doc.doc_id, doc.filename)}
                      className="ml-4 px-4 py-2 bg-red-50 text-red-600 rounded-md font-medium hover:bg-red-100 transition-colors flex items-center gap-2"
                      title="Delete document"
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
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-between items-center">
          <p className="text-sm text-gray-600">
            Supported formats: PDF, TXT, DOCX (max 50MB)
          </p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-600 text-white rounded-md font-medium hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default DocumentManager;
