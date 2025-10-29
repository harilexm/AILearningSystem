<template>
  <div class="dashboard-container">
    <h1>Course Library</h1>
    <p>Browse our available courses and start your learning journey.</p>
    
    <div v-if="isLoading" class="loading">Loading courses...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    
    <div v-else class="course-grid">
      <div v-for="course in courses" :key="course.id" class="course-card">
        <h3>{{ course.title }}</h3>
        <p class="course-author">Created by: {{ course.author }}</p>
        
        <!-- THIS IS THE FIX: Truncate the description for a cleaner look -->
        <p class="course-desc">{{ truncate(course.description, 100) }}</p>

        <RouterLink :to="{ name: 'course-details', params: { courseId: course.id } }" class="btn">
          View Course
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

const authStore = useAuthStore();
const courses = ref([]);
const isLoading = ref(true);
const error = ref('');

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { Authorization: `Bearer ${authStore.token}` }
});

const fetchCourses = async () => {
  try {
    const response = await apiClient.get('/courses');
    courses.value = response.data;
  } catch (err) {
    error.value = 'Failed to load courses. Please try again later.';
  } finally {
    isLoading.value = false;
  }
};

// --- NEW HELPER FUNCTION FOR THE UI FIX ---
const truncate = (text, length) => {
  if (!text) return '';
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
};

onMounted(fetchCourses);
</script>

<style scoped>
.dashboard-container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 1rem;
}
.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
}
.course-card {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
}
.course-card h3 { margin-top: 0; }
.course-author { font-style: italic; color: #6c757d; font-size: 0.9rem; }
.course-desc {
  flex-grow: 1; /* This is key: it pushes the button to the bottom */
  color: #495057;
  line-height: 1.5;
  margin-bottom: 1rem; /* Add some space above the button */
}
.btn {
  display: block;
  text-align: center;
  background-color: #28a745;
  color: white;
  padding: 0.75rem;
  border-radius: 5px;
  text-decoration: none;
  font-weight: bold;
  margin-top: auto; /* Pushes button to the bottom of the card */
}
.error-message { color: #dc3545; }
.loading { color: #6c757d; }
</style>