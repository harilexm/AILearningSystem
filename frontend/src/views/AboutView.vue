<template>
  <div class="about-container">
    <h1>About Our Platform</h1>
    <p>
      This project is an AI-Powered Personalized Learning System. Our mission is to
      revolutionize education by providing a learning experience that is tailored to
      each individual student's needs, pace, and learning style.
    </p>
    <h2>Our Technology</h2>
    <p>
      We leverage cutting edge technology to achieve our goals. The system is built on a modern stack:
    </p>
    <ul>
      <li><strong>PostgreSQL:</strong> A powerful, opensource object-relational database system for robust data storage.</li>
      <li><strong>Flask (Python):</strong> A lightweight and flexible web framework for our powerful backend API.</li>
      <li><strong>Vue.js:</strong> A progressive JavaScript framework for building a dynamic and responsive user interface.</li>
    </ul>
    <p>
      Our core feature is the AI engine, which analyzes student interaction data such as quiz scores, time spent on content, and learning history to recommend the most effective next steps and learning materials.
    </p>
  </div>
</template>

<style scoped>
.about-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  line-height: 1.6;
  color: #333;
}

h1, h2 {
  color: #2c3e50;
  border-bottom: 2px solid #e9ecef;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
}

ul {
  padding-left: 20px;
}

li {
  margin-bottom: 0.5rem;
}
</style>