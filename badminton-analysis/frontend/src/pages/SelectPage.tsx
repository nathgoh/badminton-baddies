import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { User, AlertCircle, Loader2 } from 'lucide-react';
import { apiClient } from '../api/client';
import { BoundingBox } from '../types';

interface PersonSelectorProps {
  videoId: string;
  frameImage: string;
  persons: BoundingBox[];
  onPersonSelected: (bbox: BoundingBox) => void;
}

function PersonSelector({ 
  frameImage, 
  persons, 
  onPersonSelected 
}: PersonSelectorProps) {
  const [selectedPerson, setSelectedPerson] = useState<number | null>(null);

  const handlePersonClick = (personId: number, bbox: BoundingBox) => {
    setSelectedPerson(personId);
    onPersonSelected(bbox);
  };

  return (
    <div className="relative">
      <img 
        src={`data:image/jpeg;base64,${frameImage}`}
        alt="Video frame"
        className="w-full h-auto rounded-lg"
      />
      
      {persons.map((person) => (
        <div
          key={person.id}
          className={`
            absolute border-2 cursor-pointer transition-all
            ${selectedPerson === person.id 
              ? 'border-blue-500 bg-blue-500 bg-opacity-20' 
              : 'border-green-500 bg-green-500 bg-opacity-10 hover:bg-opacity-20'
            }
          `}
          style={{
            left: `${(person.x / 640) * 100}%`,
            top: `${(person.y / 480) * 100}%`,
            width: `${(person.width / 640) * 100}%`,
            height: `${(person.height / 480) * 100}%`,
          }}
          onClick={() => handlePersonClick(person.id, person)}
        >
          <div className="absolute -top-6 left-0 bg-blue-500 text-white text-xs px-2 py-1 rounded">
            Person {person.id + 1}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SelectPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [frameImage, setFrameImage] = useState<string>('');
  const [persons, setPersons] = useState<BoundingBox[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<BoundingBox | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    if (!videoId) {
      navigate('/');
      return;
    }

    loadFrameAndDetectPersons();
  }, [videoId, navigate]);

  const loadFrameAndDetectPersons = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.detectPersons({ video_id: videoId });
      
      setFrameImage(response.frame_image);
      setPersons(response.persons);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load video frame');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePersonSelected = (bbox: BoundingBox) => {
    setSelectedPerson(bbox);
  };

  const handleStartAnalysis = async () => {
    if (!selectedPerson || !videoId) return;

    try {
      setIsAnalyzing(true);
      const response = await apiClient.startAnalysis({
        video_id: videoId,
        person_bbox: selectedPerson,
      });

      navigate(`/results/${videoId}?analysis_id=${response.analysis_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600">Loading video frame...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Select Player to Track
          </h1>
          <p className="text-lg text-gray-600">
            Click on the person you want to analyze in the video
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <User className="h-5 w-5 mr-2" />
              Detected Persons ({persons.length})
            </h2>
            
            {persons.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500">No persons detected in the video frame</p>
              </div>
            ) : (
              <PersonSelector
                videoId={videoId!}
                frameImage={frameImage}
                persons={persons}
                onPersonSelected={handlePersonSelected}
              />
            )}
          </div>

          {selectedPerson && (
            <div className="border-t pt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Selected: Person {selectedPerson.id + 1}
                  </h3>
                  <p className="text-sm text-gray-600">
                    Confidence: {(selectedPerson.confidence * 100).toFixed(1)}%
                  </p>
                </div>
                
                <button
                  onClick={handleStartAnalysis}
                  disabled={isAnalyzing}
                  className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Starting Analysis...
                    </>
                  ) : (
                    'Start Analysis'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => navigate('/')}
            className="text-gray-600 hover:text-gray-900"
          >
            ← Back to Upload
          </button>
        </div>
      </div>
    </div>
  );
}
