// %%
import "@loaders.gl/polyfills";
import { load } from "npm:@loaders.gl/core";
import { LASLoader } from "npm:@loaders.gl/las";

// %%
const localFile = "../sites/AGG_O_01/AGG_O_01_plot1_MGA2020_1.2.laz";
const data = await load(localFile, LASLoader, {});
// %%
console.log(data);
