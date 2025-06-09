// %%
import { Copc } from "npm:copc";
// %%
const filename = "../sites/PPO_Y_07/PPO_Y_07_MGA2020.copc.laz";
const copc = await Copc.create(filename);
console.log(copc);

// %%
const { nodes, pages } = await Copc.loadHierarchyPage(
  filename,
  copc.info.rootHierarchyPage,
);
const root = nodes["0-0-0-0"]!;
console.log(nodes);

const view = await Copc.loadPointDataView(filename, copc, root);
console.log("Dimensions:", view.dimensions);

const getters = ["X", "Y", "Z", "Intensity", "HeightAboveGround"].map(
  view.getter,
);
function getXyzi(index: number) {
  return getters.map((get) => get(index));
}
const point = getXyzi(4000);
console.log("Point:", point);
