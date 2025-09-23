import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/Home.vue";
import Products from "../views/Products.vue";
import Orders from "../views/Orders.vue";
import OrderDetail from "../views/OrderDetail.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "Home",
      component: Home,
    },
    {
      path: "/products",
      name: "Products",
      component: Products,
    },
    {
      path: "/orders",
      name: "Orders",
      component: Orders,
    },
    {
      path: "/orders/:id",
      name: "OrderDetail",
      component: OrderDetail,
      props: true,
    },
  ],
});

export default router;
