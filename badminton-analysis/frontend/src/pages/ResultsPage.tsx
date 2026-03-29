import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { 
  TrendingUp, 
  Activity, 
  Target, 
  Play, 
  AlertCircle, 
  Loader2,
  ArrowLeft 
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../api/client';
import { AnalysisResult } from '../types';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  description: string;
}

function StatCard({ title, value, icon, description }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <div className="p-2 bg-blue-100 rounded-lg mr-3">
            {icon}
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
      </div>
      <div className="text-2xl font-bold text-gray-900 mb-1">{value}</div>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}

function VideoPlayer({ videoUrl }: { videoUrl: string }) {
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
        <Play className="h-5 w-5 mr-2" />
        Annotated Video
      </h3>
      <video 
        controls 
        className="w-full rounded-lg"
        src={videoUrl}
      >
        Your browser does not support the video tag.
      </video>
    </div>
  );
}

function MovementChart({ data }: { data: Array<{ time_sec: number; distance: number }> }) {
  const chartData = data.map(point => ({
    time: `${point.time_sec.toFixed(1)}s`,
    distance: point.distance,
  }));

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
        <TrendingUp className="h-5 w-5 mr-2" />
        Movement Over Time
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip 
            formatter={(value: number) => [`${value.toFixed(2)}m`, 'Distance']}
            labelFormatter={(label) => `Time: ${label}`}
          />
          <Line 
            type="monotone" 
            dataKey="distance" 
            stroke="#3B82F6" 
            strokeWidth={2}
            dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function ResultsPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const [searchParams] = useSearchParams();
  const analysisId = searchParams.get('analysis_id');
  const navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    if (!videoId || !analysisId) {
      navigate('/');
      return;
    }

    pollForResults();
  }, [videoId, analysisId, navigate]);

  const pollForResults = async () => {
    if (!analysisId) return;

    try {
      // Poll for analysis status
      const checkStatus = async () => {
        const status = await apiClient.getAnalysisStatus(analysisId);
        
        if (status.status === 'completed') {
          // Get the results
          const result = await apiClient.getAnalysisResults(analysisId);
          setResults(result);
          setIsLoading(false);
        } else if (status.status === 'failed') {
          setError('Analysis failed. Please try again.');
          setIsLoading(false);
        } else {
          // Still processing, check again in 2 seconds
          setTimeout(checkStatus, 2000);
        }
      };

      checkStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get analysis results');
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600">Analyzing video...</p>
          <p className="text-sm text-gray-500 mt-2">This may take a few minutes</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Analysis Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  if (!results) {
    return null;
  }

  const { stats } = results;

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <button
            onClick={() => navigate('/')}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Upload
          </button>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Analysis Results
          </h1>
          <p className="text-lg text-gray-600">
            Performance metrics and annotated video for your badminton match
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Distance"
            value={`${stats.total_distance_meters}m`}
            icon={<Activity className="h-5 w-5 text-blue-600" />}
            description="Distance traveled during play"
          />
          <StatCard
            title="Average Speed"
            value={`${stats.avg_speed_mps}m/s`}
            icon={<TrendingUp className="h-5 w-5 text-green-600" />}
            description="Average movement speed"
          />
          <StatCard
            title="Court Coverage"
            value={`${stats.court_coverage_pct}%`}
            icon={<Target className="h-5 w-5 text-purple-600" />}
            description="Percentage of court covered"
          />
          <StatCard
            title="Estimated Shots"
            value={stats.estimated_shot_count}
            icon={<Activity className="h-5 w-5 text-orange-600" />}
            description="Shots detected via wrist motion"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Movement Chart */}
          <MovementChart data={stats.movement_over_time} />

          {/* Video Player */}
          <VideoPlayer videoUrl={results.annotated_video_url} />
        </div>

        {/* Additional Info */}
        <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">Analysis Details</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Performance Summary</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>• Total movement tracked over {stats.movement_over_time.length} data points</li>
                <li>• Peak speed detection during intense rallies</li>
                <li>• Court positioning analysis</li>
                <li>• Shot pattern recognition</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Technical Notes</h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>• AI-powered person tracking</li>
                <li>• Pose estimation for movement analysis</li>
                <li>• Computer vision for shot detection</li>
                <li>• Real-time video annotation</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center">
          <button
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Analyze Another Video
          </button>
        </div>
      </div>
    </div>
  );
}
