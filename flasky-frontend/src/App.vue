<script setup></script>

<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <router-link to="/" class="text-xl font-bold text-blue-600">
              Flasky Inventory
            </router-link>
          </div>
          <div class="flex items-center space-x-4">
            <router-link
              to="/products"
              class="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              Products
            </router-link>
            <router-link
              to="/orders"
              class="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium"
            >
              Orders
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto py-6 px-4">
      <router-view />
    </main>
  </div>
</template>

<style scoped></style>
