import {
  Text,
  Box,
  SimpleGrid,
  Button,
  Divider,
  Avatar,
  useColorModeValue,
  HStack,
  Spacer,
} from "@chakra-ui/react";
import Image from "next/image";
import { AiOutlineDollarCircle } from "react-icons/ai";
import { BiHomeCircle } from "react-icons/bi";
import { IoConstructOutline, IoGridOutline } from "react-icons/io5";
import { MdAutoGraph } from "react-icons/md";
import React, { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Link from "next/link";

const Sidebar: React.FC = () => {
  const bg = useColorModeValue("light.100", "dark.100");
  const [isOpen, setNavbar] = useState<Boolean>(false);
  const [number, setNumber] = useState<Number>(0);
  const router = useRouter();
  useEffect(() => {
    switch (router.pathname.split("/")[1]) {
      case "services":
        setNumber(1);
        break;
      case "billing":
        setNumber(4);
        break;
      case "models":
        setNumber(3);
        break;
      default:
        setNumber(0);
        break;
    }
  }, [router.pathname]);

  return (
    <Box
      h="100vh"
      position="fixed"
      background={bg}
      p="4"
      zIndex={50}
      style={{ textAlign: "center" }}
      onMouseEnter={() => {
        if (!isOpen) setNavbar(true);
      }}
      onMouseLeave={() => {
        if (isOpen) setNavbar(false);
      }}
      width={isOpen ? "300px" : "85px"}
      transition="width 0.2s"
      boxShadow={"md"}
    >
      <Box pt="1.5" borderRadius="xl">
        <Box h="4rem" mt={4} justifyContent="flex-start">
          <HStack>
            <Image alt="logo" src="/AI4Bharat.svg" height="50" width="50" />
            <Spacer />
            {isOpen ? (
              <Text marginLeft={4} fontSize={"x-large"} fontWeight={"bold"}>
                Dhruva
              </Text>
            ) : (
              <></>
            )}
            <Spacer />
            <Spacer />
          </HStack>
        </Box>
        <Divider />
        <SimpleGrid
          spacingY={4}
          spacingX={1}
          mt="14"
          width={"100%"}
          marginLeft={"0"}
        >
          {/* <Box>
            <Link href={"/home"}>
              <Button
                mb="2"
                ml={isOpen ? 0 : 0}
                h={10}
                variant={number === 0 ? "solid" : "ghost"}
                background={number === 0 ? "orange.500" : "transperent"}
                color={number === 0 ? "white" : "black"}
                size="l"
                boxShadow={number === 0 ? "xl" : "none"}
                w={"100%"}
                justifyContent="flex-start"
              >
                <Box>
                  <BiHomeCircle style={{ marginLeft: 12 }} size={25} />
                </Box>
                {isOpen ? (
                  <Text marginLeft={4} fontWeight={"normal"}>
                    Home
                  </Text>
                ) : (
                  <></>
                )}
              </Button>
            </Link>
          </Box> */}
          <Box>
            <Link href={"/services"}>
              <Button
                mb="2"
                ml={isOpen ? 0 : 0}
                h={10}
                w="100%"
                variant={number === 1 ? "solid" : "ghost"}
                background={number === 1 ? "orange.500" : "transperent"}
                color={number === 1 ? "white" : "black"}
                justifyContent="flex-start"
                size="l"
                boxShadow={number === 1 ? "xl" : "none"}
                transition="width 0.2s"
              >
                <Box>
                  <IoGridOutline style={{ marginLeft: 12 }} size={25} />
                </Box>
                {isOpen ? (
                  <Text marginLeft={4} fontWeight={"normal"}>
                    Services
                  </Text>
                ) : (
                  <></>
                )}
              </Button>
            </Link>
          </Box>

          {/* <Box w="100%">
            <Link href={"/models"}>
              <Button
                mb="2"
                ml={isOpen ? 0 : 0}
                h={10}
                w="100%"
                variant={number === 3 ? "solid" : "ghost"}
                background={number === 3 ? "orange.500" : "transperent"}
                color={number === 3 ? "white" : "black"}
                justifyContent="flex-start"
                size="l"
                boxShadow={number === 3 ? "xl" : "none"}
                transition="width 0.2s"
              >
                <Box>
                  <IoConstructOutline style={{ marginLeft: 12 }} size={25} />
                </Box>
                {isOpen ? (
                  <Text marginLeft={4} fontWeight={"normal"}>
                    Models
                  </Text>
                ) : (
                  <></>
                )}
              </Button>
            </Link>
          </Box>
          {/* <Box>
            <Link href={"/billing"}>
              <Button
                mb="2"
                ml={isOpen ? 0 : 0}
                h={10}
                w="100%"
                variant={number === 4 ? "solid" : "ghost"}
                background={number === 4 ? "orange.500" : "transperent"}
                color={number === 4 ? "white" : "black"}
                justifyContent="flex-start"
                size="l"
                boxShadow={number === 4 ? "xl" : "none"}
                transition="width 0.2s"
              >
                <Box>
                  <AiOutlineDollarCircle style={{ marginLeft: 12 }} size={25} />
                </Box>
                {isOpen ? (
                  <Text marginLeft={4} fontWeight={"normal"}>
                    Billing
                  </Text>
                ) : (
                  <></>
                )}
              </Button>
            </Link>
          </Box> */}

          {/* <Box>
            <Link href="/analyze">
              <Button
                mb="2"
                ml={isOpen ? 0 : 0}
                h={10}
                w="100%"
                variant={number === 2 ? "solid" : "ghost"}
                background={number === 2 ? "orange.500" : "transperent"}
                color={number === 2 ? "white" : "black"}
                justifyContent="flex-start"
                size="l"
                boxShadow={number === 2 ? "xl" : "none"}
                transition="width 0.2s"
              >
                <Box>
                  <MdAutoGraph
                    style={{ marginLeft: 12, marginRight: 12 }}
                    size={25}
                  />
                </Box>
                {isOpen ? <Text fontWeight={"normal"}> Analyze</Text> : <></>}
              </Button>
            </Link>
          </Box> */}
          {/* <Box position={"absolute"} bottom="10">
            <Box>
              <Link href="/profile">
                <Button
                  mb="2"
                  ml={isOpen ? 0 : 0}
                  h={10}
                  w={"100%"}
                  variant={number === 2 ? "solid" : "ghost"}
                  colorScheme={number === 2 ? "primary" : "transperent"}
                  justifyContent="flex-start"
                  size="l"
                  boxShadow={number === 2 ? "xl" : "none"}
                  transition="width 0.2s"
                >
                  <Box>
                    <Avatar style={{ marginLeft: 12 }} size="sm" />
                  </Box>
                  {isOpen ? (
                    <Text marginLeft={4} fontWeight={"normal"}>
                      Profile
                    </Text>
                  ) : (
                    <></>
                  )}
                </Button>
              </Link>
            </Box>
          </Box> */}
        </SimpleGrid>
      </Box>
    </Box>
  );
};

export default Sidebar;
