import React from 'react';
import VideoUploader from '../components/VideoUploader';
import { useNavigate } from 'react-router-dom';

export default function UploadPage() {
  const navigate = useNavigate();

  const handleUploadSuccess = (videoId: string) => {
    navigate(`/select/${videoId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Badminton Video Analysis
          </h1>
          <p className="text-lg text-gray-600">
            Upload your badminton video to get AI-powered performance analysis
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">
            Upload Video
          </h2>
          <VideoUploader onUploadSuccess={handleUploadSuccess} />
        </div>

        <div className="mt-8 text-center">
          <div className="text-sm text-gray-500">
            <h3 className="font-semibold mb-2">How it works:</h3>
            <ol className="text-left max-w-md mx-auto space-y-2">
              <li>1. Upload your badminton video</li>
              <li>2. Select the player you want to track</li>
              <li>3. Get detailed analysis with annotated video</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}
