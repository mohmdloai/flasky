import { createApp } from "vue";
import App from "./App.vue";
import router from "./router/router";
import { message } from "ant-design-vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import "./style.css";

const app = createApp(App);

app.use(router);
app.use(Antd);

app.config.globalProperties.$message = message;

app.mount("#app");
