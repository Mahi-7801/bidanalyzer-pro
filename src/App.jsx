
import React, { useState } from 'react';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import {
  BarChart2,
  Upload,
  FileText,
  Download,
  MessageSquare,
  Settings,
  Zap,
  Globe,
  RefreshCw,
  Search,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import './index.css';

// API Configuration - Update this after deploying to Render
const API_BASE_URL = import.meta.env.PROD
  ? 'https://your-backend-url.onrender.com'  // Replace with your actual Render backend URL
  : 'http://localhost:8000';

console.log('API Base URL:', API_BASE_URL);

function App() {
  const [view, setView] = useState('home'); // 'home' | 'result'
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [error, setError] = useState(null);

  // Data State
  const [analysisData, setAnalysisData] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [history, setHistory] = useState([]);

  // Handle Analysis
  const handleAnalyze = async () => {
    if (!selectedFile) {
      alert("Please select a file first.");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      // Assume backend runs on port 8000
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: apiKey ? { 'x-api-key': apiKey } : {},
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Analysis Failed");
      }

      const data = await response.json();
      setAnalysisData(data);
      setView('result');
      setHistory([]); // Clear chat on new file
    } catch (e) {
      setError(e.message);
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setView('home');
    setHistory([]);
    setAnalysisData(null);
    setSelectedFile(null);
    setError(null);
  };

  // Translation Handler hooked to global window for Sidebar access (quick patch)
  window.handleTranslateGlobal = async (targetLang) => {
    if (!analysisData || !analysisData.Executive_Summary) {
      alert("No analysis data to translate!");
      return;
    }
    try {
      // Send FULL DATA for deep translation
      const res = await fetch(`${API_BASE_URL}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: analysisData, target_lang: targetLang })
      });
      const result = await res.json();
      if (result.translated_data) {
        setAnalysisData(result.translated_data);
      }
    } catch (e) {
      alert("Translation failed: " + e.message);
    }
  };

  window.handleDownloadPdfGlobal = async () => {
    if (!analysisData) {
      alert("No analysis data found.");
      return;
    }

    try {
      const btn = document.querySelector(".btn-primary .animate-spin")?.closest("button");
      if (btn) btn.innerHTML = '<span class="animate-spin">Generating PDF...</span>'; // Quick visual feedback

      const res = await fetch(`${API_BASE_URL}/generate-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: analysisData })
      });

      if (res.ok) {
        // 1. Get Blob
        const blob = await res.blob();

        // 2. Try "Save As" (File System API)
        try {
          if (window.showSaveFilePicker) {
            const handle = await window.showSaveFilePicker({
              suggestedName: 'Bid_Analysis_Report.pdf',
              types: [{
                description: 'PDF Document',
                accept: { 'application/pdf': ['.pdf'] },
              }],
            });
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            alert("Report saved successfully!");
            return;
          }
        } catch (e) {
          if (e.name !== 'AbortError') console.warn("Picker failed, using fallback.");
          else return; // Cancelled
        }

        // 3. Fallback: Classic Download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Bid_Analysis_Report.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);

      } else {
        const err = await res.json();
        alert("PDF Generation Failed: " + (err.detail || "Server Error"));
      }
    } catch (e) {
      console.error(e);
      alert("PDF Error: " + e.message);
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        apiKey={apiKey}
        setApiKey={setApiKey}
        onReset={handleReset}
        view={view}
        setSelectedFile={setSelectedFile}
        selectedFile={selectedFile}
      />

      <main className="main-content">
        <MainHeader />

        {view === 'home' ? (
          <>
            <UploadSection
              onAnalyze={handleAnalyze}
              loading={loading}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile} // Allow drag-drop set
              error={error}
            />
            <FeatureCards />
          </>
        ) : (
          <ResultsView
            data={analysisData}
            question={question}
            setQuestion={setQuestion}
            history={history}
            setHistory={setHistory}
            apiKey={apiKey}
          />
        )}
      </main>
    </div>
  );
}

// --- Components ---

const Sidebar = ({ apiKey, setApiKey, onReset, view, setSelectedFile, selectedFile }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-section">
        <h3 className="sidebar-title">
          <Settings size={18} /> Controls
        </h3>
      </div>

      <div className="sidebar-section">
        <h4 className="sidebar-title">
          <FileText size={16} /> Upload Document
        </h4>

        {!apiKey && (
          <div className="input-group">
            <label className="input-label">Gemini API Key (Optional)</label>
            <input
              type="password"
              className="text-input"
              placeholder="Leave empty to use Server Key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
        )}

        <div className="input-group">
          <label className="input-label">Choose File</label>
          <input
            type="file"
            className="text-input"
            style={{ padding: '0.5rem' }}
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
          {selectedFile && <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', color: '#28a745' }}>{selectedFile.name}</div>}
        </div>
      </div>

      <div className="sidebar-section">
        <h4 className="sidebar-title">
          <Zap size={16} /> Quick Actions
        </h4>
        <button className="btn btn-outline" onClick={onReset}>
          <RefreshCw size={16} /> Clear Analysis
        </button>
      </div>

      {view === 'result' && (
        <>
          {/* Translate Button Placeholder - Logic to come later */}

          <div className="sidebar-section">
            <h4 className="sidebar-title">
              <Globe size={16} /> Translate Summary
            </h4>
            <div className="input-group">
              <select className="select-input" id="langSelect">
                {[
                  "Afrikaans", "Albanian", "Amharic", "Arabic", "Armenian", "Azerbaijani", "Basque", "Belarusian", "Bengali", "Bosnian",
                  "Bulgarian", "Catalan", "Cebuano", "Chinese (Simplified)", "Chinese (Traditional)", "Corsican", "Croatian", "Czech", "Danish", "Dutch",
                  "English", "Esperanto", "Estonian", "Finnish", "French", "Frisian", "Galician", "Georgian", "German", "Greek",
                  "Gujarati", "Haitian Creole", "Hausa", "Hawaiian", "Hebrew", "Hindi", "Hmong", "Hungarian", "Icelandic", "Igbo",
                  "Indonesian", "Irish", "Italian", "Japanese", "Javanese", "Kannada", "Kazakh", "Khmer", "Kinyarwanda", "Korean",
                  "Kurdish", "Kyrgyz", "Lao", "Latin", "Latvian", "Lithuanian", "Luxembourgish", "Macedonian", "Malagasy", "Malay",
                  "Malayalam", "Maltese", "Maori", "Marathi", "Mongolian", "Myanmar (Burmese)", "Nepali", "Norwegian", "Odia (Oriya)",
                  "Pashto", "Persian", "Polish", "Portuguese", "Punjabi", "Romanian", "Russian", "Samoan", "Scots Gaelic", "Serbian",
                  "Sesotho", "Shona", "Sindhi", "Sinhala (Sinhalese)", "Slovak", "Slovenian", "Somali", "Spanish", "Sundanese", "Swahili",
                  "Swedish", "Tagalog (Filipino)", "Tajik", "Tamil", "Tatar", "Telugu", "Thai", "Turkish", "Turkmen", "Ukrainian",
                  "Urdu", "Uyghur", "Uzbek", "Vietnamese", "Welsh", "Xhosa", "Yiddish", "Yoruba", "Zulu"
                ].map(lang => <option key={lang} value={lang}>{lang}</option>)}
              </select>
            </div>

            <button className="btn btn-primary" onClick={async (e) => {
              const btn = e.target.closest('button');
              const originalText = btn.innerHTML;
              btn.innerHTML = 'Translating...';
              btn.disabled = true;

              const lang = document.getElementById('langSelect').value;
              if (window.handleTranslateGlobal) {
                await window.handleTranslateGlobal(lang);
              }

              btn.innerHTML = originalText;
              btn.disabled = false;
            }}>
              <RefreshCw size={16} /> Translate
            </button>

            <div style={{ marginTop: '1rem' }}>
              <button className="btn btn-primary" onClick={async (e) => {
                const btn = e.target.closest('button');
                const originalText = btn.innerHTML;
                btn.innerHTML = 'Downloading...';
                btn.disabled = true;

                if (window.handleDownloadPdfGlobal) {
                  await window.handleDownloadPdfGlobal();
                }

                btn.innerHTML = originalText;
                btn.disabled = false;
              }}>
                <Download size={16} /> Download Report
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  );
};

const MainHeader = () => {
  return (
    <div className="main-header">
      <h1>📊 Bid Analyser Pro</h1>
      <p>Advanced Document Analysis & Q&A System (Gemini 2.5 Flash)</p>
    </div>
  );
};

const UploadSection = ({ onAnalyze, loading, selectedFile, setSelectedFile, error }) => {

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="upload-wrapper">
      <div
        className="upload-section"
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <h2>📄 Upload Your Bid Document</h2>
        <p>Drag and drop a PDF or TXT file to get started with the analysis</p>

        {error && (
          <div style={{ color: '#ff4d4d', background: 'rgba(255, 77, 77, 0.1)', padding: '1rem', borderRadius: '8px', marginTop: '1rem' }}>
            ⚠️ {error}
          </div>
        )}

        <div
          className="upload-area"
          onClick={!loading ? onAnalyze : undefined}
          style={{ marginTop: '2rem', cursor: loading ? 'wait' : 'pointer' }}
        >
          {loading ? (
            <div style={{ width: '100%', maxWidth: '300px' }}>
              <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <RefreshCw className="animate-spin" size={16} />
                <span style={{ fontWeight: 500 }}>Analyzing Document...</span>
              </div>
              <div className="progress-container" style={{ background: '#e2e8f0', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                <div className="progress-bar" style={{
                  background: '#667eea',
                  height: '100%',
                  width: '100%',
                  animation: 'progressIndeterminate 2s infinite linear',
                  transformOrigin: 'left'
                }} />
              </div>
              <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '8px' }}>This may take up to 30 seconds</p>
            </div>
          ) : (
            <>
              <Upload className="upload-icon" />
              <h3>{selectedFile ? 'Click to Start Analysis' : 'Select a File first'}</h3>
              <span style={{ fontSize: '0.9rem', opacity: 0.7 }}>Supported formats: PDF, TXT • Max size: 200MB</span>
            </>
          )}
        </div>
        {selectedFile && <p style={{ marginTop: '1rem', color: '#667eea' }}>Selected: {selectedFile.name}</p>}
      </div>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
};

const FeatureCards = () => {
  return (
    <div className="features-grid">
      <div className="feature-card">
        <h4><Search size={20} /> Key Information Extraction</h4>
        <ul>
          <li><CheckCircle size={14} color="#667eea" /> Tender Number & Details</li>
          <li><CheckCircle size={14} color="#667eea" /> Contract Value & EMD</li>
          <li><CheckCircle size={14} color="#667eea" /> Deadlines & Important Dates</li>
        </ul>
      </div>

      <div className="feature-card">
        <h4><Zap size={20} /> AI-Powered Analysis</h4>
        <ul>
          <li><CheckCircle size={14} color="#667eea" /> Intelligent Q&A System</li>
          <li><CheckCircle size={14} color="#667eea" /> Document Summarization</li>
          <li><CheckCircle size={14} color="#667eea" /> Progress Tracking</li>
        </ul>
      </div>
    </div>
  );
};

const ResultsView = ({ data, question, setQuestion, history, setHistory, apiKey }) => {

  if (!data) return <div>No Data</div>;

  const basicInfo = [
    { label: 'Tender Reference', value: data.Tender_Reference },
    { label: 'Issuing Authority', value: data.Issuing_Authority },
    { label: 'Project Name', value: data.Project_Name },
    { label: 'Location', value: data.Location }
  ];

  const projectDetails = [
    { label: 'Scope of Work', value: data.Scope_of_Work },
    { label: 'Contract Period', value: data.Contract_Period },
    { label: 'Technical Specifications', value: data.Technical_Specifications }
  ];

  const financials = [
    { label: 'Estimated Value', value: data.Estimated_Value },
    { label: 'EMD Amount', value: data.EMD_Amount },
    { label: 'Tender Fee', value: data.Tender_Fee },
    { label: 'Payment Terms', value: data.Payment_Terms }
  ];

  // Handle flexible dates - Important_Dates is an object with variable keys
  const dates = [];
  if (data.Important_Dates && typeof data.Important_Dates === 'object') {
    // Convert the Important_Dates object into an array of {label, value} pairs
    Object.entries(data.Important_Dates).forEach(([key, value]) => {
      dates.push({ label: key, value: value });
    });
  }
  // Fallback: if old format is used (backwards compatibility)
  if (dates.length === 0) {
    if (data.Bid_Submission_Deadline) dates.push({ label: 'Bid Submission Deadline', value: data.Bid_Submission_Deadline });
    if (data.Bid_Opening_Date) dates.push({ label: 'Bid Opening Date', value: data.Bid_Opening_Date });
    if (data.Pre_Bid_Meeting_Date) dates.push({ label: 'Pre-Bid Meeting', value: data.Pre_Bid_Meeting_Date });
  }

  const eligibility = [];

  // Handle new Eligibility object structure
  if (data.Eligibility && typeof data.Eligibility === 'object') {
    if (data.Eligibility.Min_Turnover) {
      eligibility.push({ label: 'Min Turnover', value: data.Eligibility.Min_Turnover });
    }
    if (data.Eligibility.Experience_Required) {
      eligibility.push({ label: 'Experience Required', value: data.Eligibility.Experience_Required });
    }
    if (data.Eligibility.Other_Eligibility_Criteria) {
      eligibility.push({ label: 'Other Criteria', value: data.Eligibility.Other_Eligibility_Criteria });
    }
  }
  // Fallback for old flat structure
  if (eligibility.length === 0) {
    if (data.Min_Turnover) eligibility.push({ label: 'Min Turnover', value: data.Min_Turnover });
    if (data.Experience_Required) eligibility.push({ label: 'Experience Required', value: data.Experience_Required });
  }

  // Required Documents
  if (data.Required_Documents) {
    const docs = Array.isArray(data.Required_Documents)
      ? data.Required_Documents.join(', ')
      : data.Required_Documents;
    eligibility.push({ label: 'Required Documents', value: docs });
  }

  const submissionInfo = [
    { label: 'Submission Method', value: data.Submission_Method },
    { label: 'Contact Details', value: data.Contact_Details }
  ];

  // Filter function to hide "Not Specified" rows
  const shouldShow = (val) => {
    if (!val || val === null || val === undefined || val === '') return false;
    const str = String(val).trim().toLowerCase();
    // Hide if it's "not specified", "n/a", "null", etc.
    const hideValues = ['not specified', 'n/a', 'null', 'undefined', 'none'];
    return !hideValues.some(hide => str === hide || str.includes(hide));
  };

  // Filter all arrays
  const basicInfoFiltered = basicInfo.filter(row => shouldShow(row.value));
  const projectDetailsFiltered = projectDetails.filter(row => shouldShow(row.value));
  const financialsFiltered = financials.filter(row => shouldShow(row.value));
  const datesFiltered = dates.filter(row => shouldShow(row.value));
  const eligibilityFiltered = eligibility.filter(row => shouldShow(row.value));
  const submissionInfoFiltered = submissionInfo.filter(row => shouldShow(row.value));

  const handleAsk = async () => {
    if (!question.trim()) return;

    // Add User Question to UI
    const newHistory = [...history, { type: 'question', content: question }];
    setHistory(newHistory);
    setQuestion('');

    // Simple mock logic or backend call for Q&A (requires context passing or session)
    // For this prototype, we'll simulate a generic answer or call the backend '/ask' 
    // passing the EXEC SUMMARY as context (just as a proof of concept).

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(apiKey ? { 'x-api-key': apiKey } : {}) },
        body: JSON.stringify({ question: question, context: JSON.stringify(data) })
      });

      const ansData = await response.json();
      setHistory(prev => [...prev, { type: 'answer', content: ansData.answer || "No answer found." }]);

    } catch (e) {
      setHistory(prev => [...prev, { type: 'answer', content: "Error connecting to AI." }]);
    }
  };

  return (
    <div className="animate-fade-in results-container">
      <div className="summary-card">
        <h3 className="summary-title">📊 Bid Analysis Summary</h3>

        <div className="exec-summary">
          <h4>📋 Executive Summary</h4>
          <p>{data.Executive_Summary}</p>
        </div>

        <div className="section-header">BASIC INFORMATION</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {basicInfoFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="section-header">PROJECT DETAILS</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {projectDetailsFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="section-header">KEY FINANCIALS</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {financialsFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="section-header">IMPORTANT DATES</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {datesFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="section-header">ELIGIBILITY CRITERIA</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {eligibilityFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

        <div className="section-header">SUBMISSION INFORMATION</div>
        <table className="bid-table">
          <thead>
            <tr> <th width="40%">Field</th> <th>Value</th> </tr>
          </thead>
          <tbody>
            {submissionInfoFiltered.map((row, i) => (
              <tr key={i}><td>{row.label}</td><td>{row.value}</td></tr>
            ))}
          </tbody>
        </table>

      </div>

      <div className="section-header">🔍 Ask Questions About the Document</div>
      <div className="chat-input-wrapper">
        <input
          type="text"
          className="text-input"
          placeholder="e.g. What is the penalty clause?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
        />
        <button className="btn btn-primary" style={{ width: 'auto', whiteSpace: 'nowrap' }} onClick={handleAsk}>
          <Search size={18} /> Ask
        </button>
      </div>

      {history.length > 0 && (
        <>
          <div className="section-header">💬 Question & Answer History</div>
          <div className="chat-history">
            {history.map((item, idx) => (
              <div key={idx} className={`qa-card ${item.type}`}>
                <span className="qa-label">{item.type === 'question' ? 'Q:' : 'A:'}</span>
                {item.content}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default App;
