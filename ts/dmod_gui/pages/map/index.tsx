import dynamic from "next/dynamic";

const NoSSRMap = dynamic(() => import("../../components/HydrofabricMap"), {
  ssr: false,
});

export const Map = () => {
  return <NoSSRMap />;
};

export default Map;
