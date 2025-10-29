<template>
  <div class="course-mgmt-container">
    <h1>Course Management</h1>
    
    <div class="main-grid">
      <!-- Left Column: Course List and Creation -->
      <div class="course-list-panel">
        <!-- ... (Course creation and list part is unchanged) ... -->
      </div>

      <!-- Right Column: Course Builder -->
      <div class="course-builder-panel">
        <div v-if="!selectedCourse" class="card placeholder">
          <p>Select a course on the left to start building.</p>
        </div>
        
        <div v-else>
          <h2>Building: {{ selectedCourse.title }}</h2>
          <RouterLink :to="{ name: 'course-progress', params: { courseId: selectedCourse.id } }" class="btn btn-secondary">
            View Student Progress
          </RouterLink>
          
          <!-- Modules Section -->
          <div v-for="module in selectedCourse.modules" :key="module.id" class="card module-card">
            <h3>Module {{ module.order }}: {{ module.title }}</h3>
            <ul class="content-list">
              <!-- ... (Existing content list is unchanged) ... -->
            </ul>

            <!-- MODIFIED Add New Content Form -->
            <form @submit.prevent="handleAddContent(module.id)" class="add-content-form">
              <h4>Add New Content</h4>
              <div class="content-form-grid">
                <input v-model="newContent[module.id].title" type="text" placeholder="Content Title" required/>
                <select v-model="newContent[module.id].type">
                  <option value="video">Video</option>
                  <option value="article">Article</option>
                  <option value="quiz">Quiz</option> <!-- NEW OPTION -->
                </select>
                <input v-if="newContent[module.id].type === 'video'" v-model="newContent[module.id].url" type="text" placeholder="Content URL"/>
              </div>

              <!-- NEW: QUIZ BUILDER UI -->
              <div v-if="newContent[module.id].type === 'quiz'" class="quiz-builder">
                <h5>Quiz Questions</h5>
                <div v-for="(question, qIndex) in newContent[module.id].quizData.questions" :key="qIndex" class="question-builder">
                  <input v-model="question.question" type="text" :placeholder="`Question ${qIndex + 1}`" />
                  <div v-for="(option, oIndex) in question.options" :key="oIndex" class="option-builder">
                    <input type="radio" :name="`correct_answer_${qIndex}`" :value="option" v-model="question.answer">
                    <input v-model="question.options[oIndex]" type="text" :placeholder="`Option ${oIndex + 1}`" />
                  </div>
                  <button type="button" @click="addOption(module.id, qIndex)" class="btn-tiny">Add Option</button>
                </div>
                <button type="button" @click="addQuestion(module.id)" class="btn-small">Add Question</button>
              </div>

              <button type="submit" class="btn-add-content">Add Content</button>
            </form>
          </div>

          <!-- Add New Module Form -->
          <div class="card">
            <!-- ... (This part is unchanged) ... -->
          </div>
        </div>
      </div>
    </div>
    
    <p v-if="message" class="message" :class="isError ? 'error' : 'success'">{{ message }}</p>
  </div>
</template>

<!-- REVISED SCRIPT for CourseManagementView.vue -->
<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router'; // Import RouterLink
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

// ... (most refs are unchanged) ...
const newContent = ref({}); // Use an object keyed by module ID

// Initialize the quizData structure for new content
const initializeNewContent = (moduleId) => {
  newContent.value[moduleId] = {
    title: '',
    type: 'video',
    url: '',
    body: '',
    metadata: { questions: [] } // Initialize with empty questions
  };
};

const selectCourse = async (courseId) => {
  // ... (existing logic) ...
  selectedCourse.value.modules.forEach(module => {
    initializeNewContent(module.id); // Initialize for each module
  });
};

const handleAddContent = async (moduleId) => {
  const content = newContent.value[moduleId];
  const module = selectedCourse.value.modules.find(m => m.id === moduleId);
  const nextOrder = (module.learning_contents.length || 0) + 1;
  
  // Prepare payload based on content type
  const payload = { 
    title: content.title, 
    type: content.type, 
    order: nextOrder,
    url: content.type === 'video' ? content.url : null,
    body: content.type === 'article' ? content.body : null,
    metadata: content.type === 'quiz' ? content.metadata : null
  };

  try {
    await apiClient.post(`/modules/${moduleId}/content`, payload);
    showApiMessage('Content added successfully.');
    initializeNewContent(moduleId); // Reset form
    await selectCourse(selectedCourse.value.id); // Refresh details
  } catch (err) { handleApiError(err, 'Failed to add content.'); }
};

// --- NEW QUIZ BUILDER FUNCTIONS ---
const addQuestion = (moduleId) => {
  newContent.value[moduleId].metadata.questions.push({
    question: '',
    options: ['', ''], // Start with 2 options
    answer: ''
  });
};
const addOption = (moduleId, questionIndex) => {
  newContent.value[moduleId].metadata.questions[questionIndex].options.push('');
};

</script>

<style scoped>
.main-grid { display: grid; grid-template-columns: 350px 1fr; gap: 2rem; align-items: flex-start; }
.course-list-panel .card { margin-bottom: 1rem; }
.course-builder-panel .placeholder { text-align: center; padding: 4rem; color: #888; }
.course-list { list-style: none; padding: 0; margin: 0; }
.course-list li { padding: 0.8rem 1rem; border-radius: 5px; cursor: pointer; border: 1px solid transparent; }
.course-list li:hover { background-color: #f8f9fa; }
.course-list li.selected { background-color: #e9ecef; border-color: #ccc; font-weight: bold; }
.module-card { margin-bottom: 1.5rem; }
.content-list { list-style: none; padding-left: 1rem; margin-top: 1rem; }
.content-item { background-color: #f8f9fa; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.5rem; }
.content-item-empty { color: #888; font-style: italic; }
.add-content-form { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; display: flex; gap: 0.5rem; align-items: center;}
.btn-small { padding: 0.5rem 1rem; }
.btn-secondary {
  display: inline-block;
  background-color: #6c757d;
  margin-bottom: 1.5rem;
  text-decoration: none;
}
/* General Styles from before */
.course-mgmt-container { max-width: 1200px; margin: 2rem auto; padding: 1rem; }
.card { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.form-group { margin-bottom: 1rem; }
label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
input, textarea, select { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
.btn { background-color: #007bff; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; }
.message { padding: 1rem; border-radius: 4px; text-align: center; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); }
.success { background-color: #d4edda; color: #155724; }
.error { background-color: #f8d7da; color: #721c24; }
</style>