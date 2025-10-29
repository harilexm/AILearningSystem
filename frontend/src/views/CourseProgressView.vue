<template>
  <div class="progress-container">
    <div v-if="isLoading" class="loading">Loading Progress Data...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    
    <div v-else>
      <h1>Student Progress for "{{ courseTitle }}"</h1>
      
      <div v-if="progressData.length === 0" class="no-data">
        <p>No students have started this course yet.</p>
      </div>

      <table v-else class="progress-table">
        <thead>
          <tr>
            <th>Student Name</th>
            <th>Progress</th>
            <th>Summary</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="student in progressData" :key="student.student_id">
            <td>{{ student.student_name }}</td>
            <td>
              <div class="progress-bar-container">
                <div class="progress-bar" :style="{ width: student.percentage + '%' }"></div>
              </div>
            </td>
            <td>{{ student.completed_count }} / {{ student.total_items }} items ({{ student.percentage }}%)</td>
          </tr>
        </tbody>
      </table>
    </div>
    <RouterLink to="/manage-courses" class="btn-back">&larr; Back to Course Management</RouterLink>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

const route = useRoute();
const authStore = useAuthStore();
const progressData = ref([]);
const courseTitle = ref(''); // To store the course title
const isLoading = ref(true);
const error = ref('');

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { Authorization: `Bearer ${authStore.token}` }
});

const fetchProgressData = async () => {
  const courseId = route.params.courseId;
  try {
    // We can fetch both course details and progress
    const [progressResponse, courseResponse] = await Promise.all([
        apiClient.get(`/courses/${courseId}/progress`),
        apiClient.get(`/courses/${courseId}`)
    ]);
    progressData.value = progressResponse.data;
    courseTitle.value = courseResponse.data.title;

  } catch (err) {
    error.value = 'Failed to load progress data.';
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchProgressData);
</script>

<style scoped>
.progress-container {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 2rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.progress-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 2rem;
}
.progress-table th, .progress-table td {
  border: 1px solid #ddd;
  padding: 1rem;
  text-align: left;
}
.progress-table th { background-color: #f8f9fa; }

.progress-bar-container {
  width: 100%;
  background-color: #e9ecef;
  border-radius: 5px;
  height: 20px;
}
.progress-bar {
  background-color: #28a745;
  height: 100%;
  border-radius: 5px;
  transition: width 0.5s ease-in-out;
}
.no-data, .loading, .error-message {
  text-align: center;
  padding: 3rem;
  font-size: 1.2rem;
  color: #6c757d;
}
.btn-back {
  display: inline-block;
  margin-top: 2rem;
  text-decoration: none;
  color: #007bff;
  font-weight: bold;
}
</style>