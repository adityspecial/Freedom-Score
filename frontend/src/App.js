import { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

function App() {
  const [user, setUser] = useState(null);
  const [calendarData, setCalendarData] = useState("");
  const [timePeriod, setTimePeriod] = useState("this_week");
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showManual, setShowManual] = useState(false);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user_data');
    
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    
    // Check for OAuth callback with token
    const urlParams = new URLSearchParams(window.location.search);
    const authStatus = urlParams.get('auth');
    const authToken = urlParams.get('token');
    const userEmail = urlParams.get('user');
    const userName = urlParams.get('name');
    
    if (authStatus === 'success' && authToken && userEmail) {
      // Store token and user data from OAuth callback
      localStorage.setItem('access_token', authToken);
      localStorage.setItem('user_data', JSON.stringify({
        email: userEmail,
        name: userName,
        id: userEmail
      }));
      
      setUser({
        email: userEmail,
        name: userName,
        id: userEmail
      });
      
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
    } else if (authStatus === 'error') {
      setError('Google Calendar authorization failed. Please try again.');
    }
  }, []);

  const handleGoogleLogin = async (credentialResponse) => {
    try {
      setLoading(true);
      setError("");
      
      const result = await axios.post(`${API}/auth/google`, {
        token: credentialResponse.credential
      });
      
      const { access_token, user: userData } = result.data;
      
      // Store token and user data
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user_data', JSON.stringify(userData));
      
      setUser(userData);
      
    } catch (err) {
      console.error("Google login error:", err);
      setError(err.response?.data?.detail || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLoginError = () => {
    console.error("Google login failed");
    setError("Google login failed. Please try again.");
  };

  const requestCalendarAccess = async () => {
    try {
      setLoading(true);
      setError("");
      
      const response = await axios.get(`${API}/auth/google-calendar`);
      const { authorization_url } = response.data;
      
      // Redirect to Google OAuth
      window.location.href = authorization_url;
      
    } catch (err) {
      console.error("Calendar access error:", err);
      setError(err.response?.data?.detail || "Failed to request calendar access.");
      setLoading(false);
    }
  };

  const analyzeCalendarAuto = async () => {
    setLoading(true);
    setError("");
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.post(
        `${API}/analyze-calendar-auto?time_period=${timePeriod}`,
        {},
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );
      
      setAnalysis(response.data);
    } catch (err) {
      console.error("Auto analysis error:", err);
      if (err.response?.status === 401) {
        setError("Calendar access required. Please authorize Google Calendar access first.");
      } else {
        setError(err.response?.data?.detail || "Failed to analyze calendar. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  const analyzeCalendarManual = async () => {
    if (!calendarData.trim()) {
      setError("Please paste your schedule data first!");
      return;
    }

    setLoading(true);
    setError("");
    
    try {
      const response = await axios.post(`${API}/analyze-calendar`, {
        calendar_data: calendarData,
        time_period: timePeriod
      });
      
      setAnalysis(response.data);
    } catch (err) {
      console.error("Manual analysis error:", err);
      setError(err.response?.data?.detail || "Failed to analyze your freedom. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_data');
    setUser(null);
    setAnalysis(null);
    setCalendarData("");
    setError("");
    setShowManual(false);
  };

  const resetAnalysis = () => {
    setAnalysis(null);
    setCalendarData("");
    setError("");
  };

  const getFreedomColor = (percentage) => {
    if (percentage >= 70) return "text-green-400";
    if (percentage >= 40) return "text-yellow-400";
    return "text-red-400";
  };

  const getFreedomGradient = (percentage) => {
    if (percentage >= 70) return "from-green-400 to-blue-500";
    if (percentage >= 40) return "from-yellow-400 to-orange-500";
    return "from-red-400 to-red-600";
  };

  // Manual Analysis Mode (No Login Required)
  if (showManual) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-900 via-blue-900 to-blue-800 relative overflow-hidden">
        {/* Fireworks Animation Background */}
        <div className="absolute inset-0 opacity-10">
          <div className="firework firework-1"></div>
          <div className="firework firework-2"></div>
          <div className="firework firework-3"></div>
        </div>
        
        <div className="container mx-auto px-4 py-8 relative z-10">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="flex items-center justify-center mb-4">
              <span className="text-6xl mr-4">🇺🇸</span>
              <h1 className="text-5xl font-bold bg-gradient-to-r from-red-400 via-white to-blue-400 bg-clip-text text-transparent">
                Liberty Tracker
              </h1>
              <span className="text-6xl ml-4">🎆</span>
            </div>
            <p className="text-2xl text-white font-semibold mb-2">
              Life, Liberty, and the Pursuit of Free Time
            </p>
            <p className="text-lg text-gray-200 max-w-2xl mx-auto">
              Manual analysis mode - discover how much of your time is truly free
            </p>
            <button
              onClick={() => setShowManual(false)}
              className="mt-4 text-red-300 hover:text-red-200 underline"
            >
              ← Back to Google Login
            </button>
          </div>

          {!analysis ? (
            <div className="max-w-4xl mx-auto">
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-2xl">
                <div className="mb-6">
                  <label className="block text-white text-lg font-semibold mb-3">
                    🗽 Time Period Analysis
                  </label>
                  <select 
                    value={timePeriod}
                    onChange={(e) => setTimePeriod(e.target.value)}
                    className="w-full p-3 bg-blue-900/50 border border-white/30 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  >
                    <option value="today">Today</option>
                    <option value="this week">This Week</option>
                    <option value="this month">This Month</option>
                    <option value="recent days">Recent Days</option>
                  </select>
                </div>

                <div className="mb-6">
                  <label className="block text-white text-lg font-semibold mb-3">
                    📅 Paste Your Schedule Data
                  </label>
                  <p className="text-gray-200 text-sm mb-3">
                    Copy and paste your calendar events to calculate your time freedom percentage.
                    Let's see how much liberty you truly have!
                  </p>
                  <textarea
                    value={calendarData}
                    onChange={(e) => setCalendarData(e.target.value)}
                    placeholder="Paste your schedule here... 

Example:
9:00 AM - 10:00 AM: Team Meeting
10:00 AM - 11:30 AM: Project Review
2:00 PM - 3:00 PM: Client Call
3:30 PM - 4:30 PM: Planning Session
..."
                    className="w-full h-64 p-4 bg-blue-900/50 border border-white/30 rounded-lg text-white placeholder-gray-300 focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                  />
                </div>

                {error && (
                  <div className="mb-6 p-4 bg-red-800/50 border border-red-500 rounded-lg">
                    <p className="text-red-200">{error}</p>
                  </div>
                )}

                <button
                  onClick={analyzeCalendarManual}
                  disabled={loading || !calendarData.trim()}
                  className="w-full py-4 px-6 bg-gradient-to-r from-red-600 via-white to-blue-600 hover:from-red-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-700 text-blue-900 font-bold rounded-lg transition-all duration-300 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed shadow-lg"
                >
                  {loading ? (
                    <div className="flex items-center justify-center text-white">
                      <div className="animate-spin rounded-full h-6 w-6 border-2 border-white border-t-transparent mr-3"></div>
                      🎇 Calculating Your Freedom...
                    </div>
                  ) : (
                    "🗽 Calculate My Time Freedom"
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Results Display */
            <div className="max-w-4xl mx-auto">
              {/* Freedom Score */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-2xl mb-8 text-center">
                <div className="flex items-center justify-center mb-4">
                  <span className="text-4xl mr-4">🎆</span>
                  <div className={`text-8xl font-bold bg-gradient-to-r ${getFreedomGradient(analysis.independence_percentage)} bg-clip-text text-transparent`}>
                    {analysis.independence_percentage}%
                  </div>
                  <span className="text-4xl ml-4">🎆</span>
                </div>
                <div className="text-2xl text-white font-semibold mb-4">
                  🗽 TIME FREEDOM 🗽
                </div>
                <div className="text-xl text-gray-200 max-w-2xl mx-auto leading-relaxed">
                  {analysis.witty_message}
                </div>
              </div>

              {/* Freedom Stats */}
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
                  <h3 className="text-xl font-bold text-white mb-4">📊 Liberty Stats</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-200">Total Commitments:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.total_meetings}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Hours Occupied:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.total_hours}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Avg Duration:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.avg_meeting_length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Longest Free Block:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.longest_meeting_free_block}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
                  <h3 className="text-xl font-bold text-white mb-4">🚀 Freedom Strategies</h3>
                  <ul className="space-y-2">
                    {analysis.recommendations.map((rec, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-red-400 mr-2">⭐</span>
                        <span className="text-gray-200 text-sm">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Detailed Analysis */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-lg mb-8">
                <h3 className="text-2xl font-bold text-white mb-4">🎯 Your Freedom Declaration</h3>
                <p className="text-gray-200 leading-relaxed whitespace-pre-line">
                  {analysis.detailed_analysis}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="text-center">
                <button
                  onClick={resetAnalysis}
                  className="py-3 px-8 bg-gradient-to-r from-blue-600 to-red-600 hover:from-blue-700 hover:to-red-700 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
                >
                  🎆 Analyze Another Period
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Login Screen
  if (!user) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <div className="min-h-screen bg-gradient-to-br from-red-900 via-blue-900 to-blue-800 relative overflow-hidden flex items-center justify-center">
          {/* Hero Background */}
          <div 
            className="absolute inset-0 opacity-20 bg-cover bg-center"
            style={{
              backgroundImage: `url('https://images.unsplash.com/photo-1498174979972-c9de7e6a93d6')`
            }}
          ></div>
          
          {/* Fireworks Animation */}
          <div className="absolute inset-0 opacity-30">
            <div className="firework firework-1"></div>
            <div className="firework firework-2"></div>
            <div className="firework firework-3"></div>
          </div>
          
          <div className="max-w-md w-full mx-4 relative z-10">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-2xl text-center">
              <div className="flex items-center justify-center mb-6">
                <span className="text-6xl mr-4">🇺🇸</span>
                <div>
                  <h1 className="text-4xl font-bold bg-gradient-to-r from-red-400 via-white to-blue-400 bg-clip-text text-transparent">
                    Liberty Tracker
                  </h1>
                  <p className="text-white text-sm mt-1">Time Freedom Calculator</p>
                </div>
                <span className="text-6xl ml-4">🎆</span>
              </div>
              
              <p className="text-xl text-white font-semibold mb-2">
                Life, Liberty, and the Pursuit of Free Time
              </p>
              
              <p className="text-gray-200 mb-8">
                Declare your independence from busy schedules! Connect your Google Calendar to discover 
                how much of your time is truly free.
              </p>
              
              {error && (
                <div className="mb-6 p-4 bg-red-800/50 border border-red-500 rounded-lg">
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              )}
              
              <div className="mb-6">
                <GoogleLogin
                  onSuccess={handleGoogleLogin}
                  onError={handleGoogleLoginError}
                  theme="filled_blue"
                  size="large"
                  text="signin_with"
                  shape="rectangular"
                  logo_alignment="left"
                />
              </div>
              
              {loading && (
                <div className="mb-6 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-2 border-red-400 border-t-transparent mr-3"></div>
                  <span className="text-gray-200">Signing in...</span>
                </div>
              )}
              
              <div className="mt-8 pt-6 border-t border-white/20">
                <button
                  onClick={() => setShowManual(true)}
                  className="text-red-300 hover:text-red-200 text-sm underline"
                >
                  🗽 Or analyze manually without Google login
                </button>
              </div>
            </div>
          </div>
        </div>
      </GoogleOAuthProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="min-h-screen bg-gradient-to-br from-red-900 via-blue-900 to-blue-800 relative overflow-hidden">
        {/* Background Elements */}
        <div 
          className="absolute inset-0 opacity-10 bg-cover bg-center"
          style={{
            backgroundImage: `url('https://images.unsplash.com/photo-1498931299472-f7a63a5a1cfa')`
          }}
        ></div>
        
        <div className="container mx-auto px-4 py-8 relative z-10">
          {/* Header */}
          <div className="text-center mb-12">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center">
                <span className="text-5xl mr-4">🇺🇸</span>
                <h1 className="text-5xl font-bold bg-gradient-to-r from-red-400 via-white to-blue-400 bg-clip-text text-transparent">
                  Liberty Tracker
                </h1>
                <span className="text-5xl ml-4">🎆</span>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-white font-semibold">{user.name}</p>
                  <p className="text-gray-300 text-sm">{user.email}</p>
                </div>
                <button
                  onClick={logout}
                  className="px-4 py-2 bg-red-700/50 hover:bg-red-600/50 text-white rounded-lg transition-colors border border-white/20"
                >
                  Logout
                </button>
              </div>
            </div>
            <p className="text-xl text-white max-w-2xl mx-auto">
              Your Google Calendar is connected! Let's calculate your time freedom and declare independence from busy schedules.
            </p>
          </div>

          {!analysis ? (
            /* Analysis Options */
            <div className="max-w-4xl mx-auto">
              <div className="grid md:grid-cols-2 gap-8">
                {/* Automatic Analysis */}
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-lg">
                  <h3 className="text-2xl font-bold text-white mb-4 flex items-center">
                    <span className="bg-gradient-to-r from-blue-400 to-red-500 w-3 h-3 rounded-full mr-3"></span>
                    🗽 Automatic Freedom Analysis
                  </h3>
                  <p className="text-gray-200 mb-6">
                    Connect your Google Calendar to automatically calculate your time freedom percentage.
                  </p>
                  
                  <div className="mb-6">
                    <label className="block text-white text-lg font-semibold mb-3">
                      📅 Time Period
                    </label>
                    <select 
                      value={timePeriod}
                      onChange={(e) => setTimePeriod(e.target.value)}
                      className="w-full p-3 bg-blue-900/50 border border-white/30 rounded-lg text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    >
                      <option value="today">Today</option>
                      <option value="this_week">This Week</option>
                      <option value="this_month">This Month</option>
                      <option value="recent_days">Recent Days</option>
                    </select>
                  </div>

                  <div className="space-y-4">
                    <button
                      onClick={requestCalendarAccess}
                      className="w-full py-3 px-6 bg-gradient-to-r from-blue-600 to-red-600 hover:from-blue-700 hover:to-red-700 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105"
                    >
                      🎯 Authorize Google Calendar
                    </button>
                    
                    <button
                      onClick={analyzeCalendarAuto}
                      disabled={loading}
                      className="w-full py-3 px-6 bg-gradient-to-r from-red-600 to-blue-600 hover:from-red-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
                    >
                      {loading ? "🎇 Calculating..." : "🗽 Calculate My Freedom"}
                    </button>
                  </div>
                </div>

                {/* Manual Analysis */}
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-lg">
                  <h3 className="text-2xl font-bold text-white mb-4 flex items-center">
                    <span className="bg-gradient-to-r from-red-400 to-blue-500 w-3 h-3 rounded-full mr-3"></span>
                    📝 Manual Freedom Analysis
                  </h3>
                  <p className="text-gray-200 mb-6">
                    Or paste your schedule data manually for freedom calculation.
                  </p>
                  
                  <div className="mb-4">
                    <textarea
                      value={calendarData}
                      onChange={(e) => setCalendarData(e.target.value)}
                      placeholder="Paste your schedule here...

Example:
9:00 AM - 10:00 AM: Team Meeting
10:00 AM - 11:30 AM: Project Review
..."
                      className="w-full h-32 p-4 bg-blue-900/50 border border-white/30 rounded-lg text-white placeholder-gray-300 focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none text-sm"
                    />
                  </div>

                  <button
                    onClick={analyzeCalendarManual}
                    disabled={loading || !calendarData.trim()}
                    className="w-full py-3 px-6 bg-gradient-to-r from-red-600 to-blue-600 hover:from-red-700 hover:to-blue-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
                  >
                    {loading ? "🎇 Analyzing..." : "🎆 Analyze Manual Data"}
                  </button>
                </div>
              </div>

              {error && (
                <div className="mt-8 p-4 bg-red-800/50 border border-red-500 rounded-lg max-w-2xl mx-auto">
                  <p className="text-red-200 text-center">{error}</p>
                </div>
              )}
            </div>
          ) : (
            /* Results Display */
            <div className="max-w-4xl mx-auto">
              {/* Freedom Score */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-2xl mb-8 text-center">
                <div className="flex items-center justify-center mb-4">
                  <span className="text-4xl mr-4">🎆</span>
                  <div className={`text-8xl font-bold bg-gradient-to-r ${getFreedomGradient(analysis.independence_percentage)} bg-clip-text text-transparent`}>
                    {analysis.independence_percentage}%
                  </div>
                  <span className="text-4xl ml-4">🎆</span>
                </div>
                <div className="text-2xl text-white font-semibold mb-4">
                  🗽 TIME FREEDOM 🗽
                </div>
                <div className="text-xl text-gray-200 max-w-2xl mx-auto leading-relaxed">
                  {analysis.witty_message}
                </div>
              </div>

              {/* Stats and Recommendations */}
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
                  <h3 className="text-xl font-bold text-white mb-4">📊 Liberty Stats</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-200">Total Commitments:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.total_meetings}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Hours Occupied:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.total_hours}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Avg Duration:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.avg_meeting_length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-200">Longest Free Block:</span>
                      <span className="text-white font-semibold">{analysis.meeting_stats.longest_meeting_free_block}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-lg">
                  <h3 className="text-xl font-bold text-white mb-4">🚀 Freedom Strategies</h3>
                  <ul className="space-y-2">
                    {analysis.recommendations.map((rec, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-red-400 mr-2">⭐</span>
                        <span className="text-gray-200 text-sm">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Detailed Analysis */}
              <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20 shadow-lg mb-8">
                <h3 className="text-2xl font-bold text-white mb-4">🎯 Your Freedom Declaration</h3>
                <p className="text-gray-200 leading-relaxed whitespace-pre-line">
                  {analysis.detailed_analysis}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="text-center">
                <button
                  onClick={resetAnalysis}
                  className="py-3 px-8 bg-gradient-to-r from-blue-600 to-red-600 hover:from-blue-700 hover:to-red-700 text-white font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
                >
                  🎆 Analyze Another Period
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}

export default App;