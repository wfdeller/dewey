import { useState, useEffect } from 'react';
import { Typography, Steps, Button, Space, Card, App } from 'antd';
import { ArrowLeftOutlined, ArrowRightOutlined, UploadOutlined, CheckOutlined } from '@ant-design/icons';
import {
  FileUploadStep,
  FieldMappingStep,
  MatchingStrategyStep,
  ImportProgressStep,
} from '../components/voter-import';
import {
  useUploadFileMutation,
  useAnalyzeJobMutation,
  useConfirmMappingsMutation,
  useStartImportMutation,
  useJobQuery,
  useJobProgressQuery,
  useMatchingStrategiesQuery,
  AnalysisResponse,
} from '../services/voterImportService';
import { getErrorMessage } from '../services/api';

const { Title, Text } = Typography;

const STEPS = [
  { title: 'Upload', description: 'Select CSV file' },
  { title: 'Map Fields', description: 'Review mappings' },
  { title: 'Matching', description: 'Choose strategy' },
  { title: 'Import', description: 'Process records' },
];

export default function VoterImport() {
  const { message } = App.useApp();

  // Step state
  const [currentStep, setCurrentStep] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);

  // Form state
  const [confirmedMappings, setConfirmedMappings] = useState<Record<string, string | null>>({});
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [createUnmatched, setCreateUnmatched] = useState<boolean>(true);

  // Queries and mutations
  const { data: strategies } = useMatchingStrategiesQuery();
  const { data: job } = useJobQuery(jobId);
  const { data: progress } = useJobProgressQuery(
    jobId,
    job?.status === 'processing'
  );

  const uploadMutation = useUploadFileMutation();
  const analyzeMutation = useAnalyzeJobMutation();
  const confirmMutation = useConfirmMappingsMutation();
  const startMutation = useStartImportMutation();

  // Auto-advance when job completes
  useEffect(() => {
    if (job?.status === 'completed' || job?.status === 'failed') {
      // Stay on progress step to show results
    }
  }, [job?.status]);

  // Handle file upload
  const handleFileSelect = async (file: File) => {
    try {
      const newJob = await uploadMutation.mutateAsync(file);
      setJobId(newJob.id);

      // Immediately analyze
      const analysis = await analyzeMutation.mutateAsync(newJob.id);
      setAnalysisData(analysis);

      // Initialize confirmed mappings from suggestions
      const initialMappings: Record<string, string | null> = {};
      Object.entries(analysis.suggested_mappings).forEach(([header, mapping]) => {
        initialMappings[header] = mapping.field;
      });
      setConfirmedMappings(initialMappings);

      // Set suggested strategy
      setSelectedStrategy(analysis.suggested_matching_strategy);

      // Advance to mapping step
      setCurrentStep(1);
      message.success('File uploaded and analyzed');
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  // Handle mapping change
  const handleMappingChange = (header: string, field: string | null) => {
    setConfirmedMappings((prev) => ({
      ...prev,
      [header]: field,
    }));
  };

  // Handle strategy change
  const handleStrategyChange = (strategy: string) => {
    setSelectedStrategy(strategy);
  };

  // Handle next step
  const handleNext = async () => {
    if (currentStep === 1) {
      // Moving from mapping to strategy
      setCurrentStep(2);
    } else if (currentStep === 2) {
      // Confirm mappings and start import
      try {
        await confirmMutation.mutateAsync({
          jobId: jobId!,
          data: {
            confirmed_mappings: confirmedMappings,
            matching_strategy: selectedStrategy,
            create_unmatched: createUnmatched,
          },
        });

        await startMutation.mutateAsync(jobId!);
        setCurrentStep(3);
        message.success('Import started');
      } catch (error) {
        message.error(getErrorMessage(error));
      }
    }
  };

  // Handle back
  const handleBack = () => {
    if (currentStep > 0 && currentStep < 3) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Handle new import
  const handleNewImport = () => {
    setCurrentStep(0);
    setJobId(null);
    setAnalysisData(null);
    setConfirmedMappings({});
    setSelectedStrategy('');
    setCreateUnmatched(true);
  };

  // Check if can proceed
  const canProceed = () => {
    if (currentStep === 1) {
      // Need at least one mapping
      return Object.values(confirmedMappings).some((v) => v);
    }
    if (currentStep === 2) {
      return !!selectedStrategy;
    }
    return false;
  };

  // Loading states
  const isLoading =
    uploadMutation.isPending ||
    analyzeMutation.isPending ||
    confirmMutation.isPending ||
    startMutation.isPending;

  return (
    <div>
      <Title level={2}>Import Voter File</Title>
      <Text type="secondary">
        Upload a CSV voter file to import or update contacts with voting history.
      </Text>

      <Card style={{ marginTop: 24 }}>
        <Steps
          current={currentStep}
          items={STEPS}
          style={{ marginBottom: 32 }}
        />

        <div style={{ minHeight: 400 }}>
          {currentStep === 0 && (
            <FileUploadStep
              onFileSelect={handleFileSelect}
              isLoading={isLoading}
              error={uploadMutation.error ? getErrorMessage(uploadMutation.error) : null}
            />
          )}

          {currentStep === 1 && analysisData && (
            <FieldMappingStep
              headers={analysisData.headers}
              suggestedMappings={analysisData.suggested_mappings}
              voteHistoryColumns={analysisData.vote_history_columns}
              confirmedMappings={confirmedMappings}
              onMappingChange={handleMappingChange}
            />
          )}

          {currentStep === 2 && analysisData && strategies && (
            <MatchingStrategyStep
              strategies={strategies.strategies}
              suggestedStrategy={analysisData.suggested_matching_strategy}
              suggestedReason={analysisData.matching_strategy_reason}
              selectedStrategy={selectedStrategy}
              onStrategyChange={handleStrategyChange}
              createUnmatched={createUnmatched}
              onCreateUnmatchedChange={setCreateUnmatched}
            />
          )}

          {currentStep === 3 && job && (
            <ImportProgressStep
              job={job}
              progress={progress || null}
            />
          )}
        </div>

        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
          <div>
            {currentStep > 0 && currentStep < 3 && (
              <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
                Back
              </Button>
            )}
          </div>

          <Space>
            {currentStep === 3 && (job?.status === 'completed' || job?.status === 'failed') && (
              <Button type="primary" icon={<UploadOutlined />} onClick={handleNewImport}>
                Import Another File
              </Button>
            )}

            {currentStep > 0 && currentStep < 3 && (
              <Button
                type="primary"
                icon={currentStep === 2 ? <CheckOutlined /> : <ArrowRightOutlined />}
                onClick={handleNext}
                loading={isLoading}
                disabled={!canProceed()}
              >
                {currentStep === 2 ? 'Start Import' : 'Next'}
              </Button>
            )}
          </Space>
        </div>
      </Card>
    </div>
  );
}
