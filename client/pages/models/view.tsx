import {
  Box,
  Heading,
  Stack,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Text,
  Grid,
  GridItem,
  Select,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
} from "@chakra-ui/react";
import ContentLayout from "../../components/Layouts/ContentLayout";
import { useRouter } from "next/router";
import { useState, useEffect } from "react";
import useMediaQuery from "../../hooks/useMediaQuery";
import { dhruvaConfig, lang2label } from "../../config/config";
import axios from "axios";
import Head from "next/head";

interface LanguageConfig {
  sourceLanguage: string;
  targetLanguage: string;
}

interface Benchmark {
  benchmarkId: string;
  name: string;
  description: string;
  domain: string;
  createdOn: number;
  languages: {
    sourceLanguage: string;
    targetLanguage: string;
  };
  score: [
    {
      metricName: string;
      score: string;
    }
  ];
}

interface Model {
  modelId: string;
  version: string;
  submittedOn: number;
  updatedOn: number;
  name: string;
  description: string;
  refUrl: string;
  task: {
    type: string;
  };
  languages: LanguageConfig[];
  benchmarks: Benchmark[];
}

export default function ViewModel({ ...props }) {
  const router = useRouter();
  const smallscreen = useMediaQuery("(max-width: 1080px)");

  const [modelInfo, setModelInfo] = useState<Model>({
    modelId: "",
    version: "",
    submittedOn: 1,
    updatedOn: 1,
    name: "",
    description: "",
    refUrl: "",
    task: {
      type: "",
    },
    languages: [],
    benchmarks: [],
  });

  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [benchmarkMetrics, setBenchmarkMetrics] = useState<string[]>([]);
  const [benchmarkMetric, setBenchmarkMetric] = useState<string>("");
  const [benchmarkDatasets, setBenchmarkDatasets] = useState<string[]>([]);
  const [benchmarkDataset, setBenchmarkDataset] = useState<string>("");
  const [benchmarkValues, setBenchmarkValues] = useState<Benchmark[]>([]);

  useEffect(() => {
    if (router.isReady) {
      const modelId = router.query["modelId"];
      axios({
        method: "POST",
        url: dhruvaConfig.viewModel,
        data: {
          modelId: modelId,
        },
      }).then((response) => {
        setModelInfo(response.data);
        setBenchmarks(response.data.benchmarks);
      });
    }
  }, [router.isReady]);

  useEffect(() => {
    const metrics = new Set();
    const datasets = new Set();
    benchmarks.forEach((benchmark) => {
      benchmark["score"].forEach((score) => {
        metrics.add(score["metricName"]);
      });
      datasets.add(benchmark["name"]);
    });
    const currentBenchmarkDatasets = Array.from(datasets) as string[];
    const currentBenchmarkMetrics = Array.from(metrics) as string[];
    setBenchmarkMetrics(currentBenchmarkMetrics);
    setBenchmarkMetric(currentBenchmarkMetrics[0]);
    setBenchmarkDatasets(currentBenchmarkDatasets);
    setBenchmarkDataset(currentBenchmarkDatasets[0]);
  }, [benchmarks]);

  useEffect(() => {
    const currentBenchmarks = benchmarks.filter(
      (benchmark) => benchmark["name"] === benchmarkDataset
    );

    const currentMetricBenchmarks = [];
    currentBenchmarks.forEach((benchmark) => {
      benchmark["score"].forEach((score) => {
        if (score["metricName"] === benchmarkMetric) {
          const benchmarkObj = {};
          benchmarkObj["value"] = benchmark["score"][0]["score"];
          benchmarkObj["language"] = benchmark["languages"]["targetLanguage"]
            ? `${benchmark["languages"]["sourceLanguage"]}-${benchmark["languages"]["targetLanguage"]}`
            : benchmark["languages"]["sourceLanguage"];
          currentMetricBenchmarks.push(benchmarkObj);
        }
      });
    });

    setBenchmarkValues(currentMetricBenchmarks);
  }, [benchmarkMetric, benchmarkDataset]);

  return (
    <>
      {" "}
      <Head>
        <title>View Model</title>
      </Head>{" "}
      <ContentLayout>
        {smallscreen ? (
          <Grid
            ml="1rem"
            mr="1rem"
            mb="1rem"
            pl="1rem"
            pr="1rem"
            pt="1rem"
            pb="1rem"
            minH={"10vh"}
            minW={"90vw"}
            maxW={"90vw"}
            gap={10}
          >
            <GridItem p="1rem" bg="white">
              <Stack spacing={10} direction={"row"}>
                <Heading>{modelInfo["name"]}</Heading>
              </Stack>
              <Tabs isFitted>
                <TabList aria-orientation="vertical" mb="1em">
                  <Tab _selected={{ textColor: "#DD6B20" }}>Details</Tab>
                </TabList>
                <TabPanels>
                  <TabPanel>
                    <Stack spacing={5}>
                      <Text className="dview-service-description">
                        {modelInfo["description"]}
                      </Text>
                      <Stack>
                        <Text className="dview-service-info-item">
                          Model Version : {modelInfo["version"]}
                        </Text>
                        <Text className="dview-service-info-item">
                          Model Type : {modelInfo["task"]["type"]}
                        </Text>
                        <Text className="dview-service-info-item">
                          Submitted On :{" "}
                          {new Date(modelInfo["submittedOn"]).toDateString()}
                        </Text>
                        <Text className="dview-service-info-item">
                          Updated On :{" "}
                          {new Date(modelInfo["updatedOn"]).toDateString()}
                        </Text>
                      </Stack>
                    </Stack>
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </GridItem>
            <GridItem p="1rem" bg="white">
              <Stack spacing={2.5}>
                <Box m="1rem" className="dview-service-try-title-box">
                  <Heading className="dview-service-try-title">
                    Benchmarks
                  </Heading>
                </Box>
                <Stack spacing={5}>
                  <Stack direction={"row"}>
                    <Text className="dview-service-try-option-title">
                      Metric :{" "}
                    </Text>
                  </Stack>
                  <Accordion
                    defaultIndex={[0]}
                    overflow={"hidden"}
                    allowMultiple
                  ></Accordion>
                </Stack>
              </Stack>
            </GridItem>
          </Grid>
        ) : (
          <Grid
            templateColumns="repeat(2, 1fr)"
            gap={5}
            className="service-view"
            bg="light.100"
          >
            <GridItem p="1rem" bg="white">
              <Stack spacing={10} direction={"row"}>
                <Heading>{modelInfo["name"]}</Heading>
              </Stack>
              <Tabs isFitted>
                <TabList aria-orientation="vertical" mb="1em">
                  <Tab _selected={{ textColor: "#DD6B20" }}>Details</Tab>
                </TabList>
                <TabPanels>
                  <TabPanel>
                    <Stack spacing={5}>
                      <Text className="dview-service-description">
                        {modelInfo["description"]}
                      </Text>
                      <Stack>
                        <Text className="dview-service-info-item">
                          Model Version : {modelInfo["version"]}
                        </Text>
                        <Text className="dview-service-info-item">
                          Model Type : {modelInfo["task"]["type"]}
                        </Text>
                        <Text className="dview-service-info-item">
                          Submitted On :{" "}
                          {new Date(modelInfo["submittedOn"]).toDateString()}
                        </Text>
                        <Text className="dview-service-info-item">
                          Updated On :{" "}
                          {new Date(modelInfo["updatedOn"]).toDateString()}
                        </Text>
                      </Stack>
                    </Stack>
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </GridItem>
            <GridItem p="1rem" bg="white">
              <Stack spacing={2.5}>
                <Box m="1rem" className="dview-service-try-title-box">
                  <Heading className="dview-service-try-title">
                    Benchmarks
                  </Heading>
                </Box>
                <Stack spacing={5}>
                  <Stack direction={"row"}>
                    <Text className="dview-service-try-option-title">
                      Metric :{" "}
                    </Text>
                    <Select
                      value={benchmarkMetric}
                      onChange={(e) => {
                        setBenchmarkMetric(e.target.value);
                      }}
                    >
                      {benchmarkMetrics.map((metric) => {
                        return (
                          <option key={metric} value={metric}>
                            {metric.toUpperCase()}
                          </option>
                        );
                      })}
                    </Select>
                  </Stack>
                  <Stack direction={"row"}>
                    <Text className="dview-service-try-option-title">
                      Dataset :{" "}
                    </Text>
                    <Select
                      value={benchmarkDataset}
                      onChange={(e) => {
                        setBenchmarkDataset(e.target.value);
                      }}
                    >
                      {benchmarkDatasets.map((dataset) => {
                        return (
                          <option key={dataset} value={dataset}>
                            {dataset.toUpperCase()}
                          </option>
                        );
                      })}
                    </Select>
                  </Stack>
                  <SimpleGrid
                    p="1rem"
                    w="100%"
                    h="auto"
                    bg="orange.100"
                    borderRadius={15}
                    columns={2}
                    spacingX="40px"
                    spacingY="20px"
                  >
                    {benchmarkValues.map((benchmark) => {
                      return (
                        <Stat>
                          <StatLabel>
                            {benchmarkMetric.toUpperCase()} Score
                          </StatLabel>
                          <StatNumber>{benchmark["value"]}</StatNumber>
                          <StatHelpText>{benchmark["language"]}</StatHelpText>
                        </Stat>
                      );
                    })}
                  </SimpleGrid>
                </Stack>
              </Stack>
            </GridItem>
          </Grid>
        )}
      </ContentLayout>
    </>
  );
}
