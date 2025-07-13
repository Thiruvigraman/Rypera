<h1>🎬 Telegram Movie Bot</h1>

<p>
A private Telegram bot for managing and sharing movie files efficiently. Built with <strong>Flask</strong>, <strong>MongoDB</strong>, and <strong>Discord Webhooks</strong>, and hosted on <strong>Render</strong>, this bot provides admin-only control, automated message cleanup, and real-time logging.
</p>

<h2>🚀 Features</h2>
<ul>
  <li>✅ Movie files stored in MongoDB</li>
  <li>✅ Auto-delete sent files after 15 minutes to avoid copyright issues</li>
  <li>✅ Cleans up active file messages after restarts (post-restart cleanup)</li>
  <li>✅ Logs admin actions like uploads, deletes, and renames </li>
  <li>✅ Logs bot status, errors, and crashes </li>
  <li>✅ Health check command for uptime, memory, and CPU usage</li>
  <li>✅ Broadcast announcements to all users with built-in rate limiting</li>
</ul>

<h2>🛠️ Admin Commands</h2>
<table>
  <thead>
    <tr>
      <th>Command</th>
      <th>Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><em>Upload + Name</em></td>
      <td>Upload a movie file and assign a unique name</td>
    </tr>
    <tr>
      <td><code>/list_files</code></td>
      <td>List all stored movie files</td>
    </tr>
    <tr>
      <td><code>/rename_file</code></td>
      <td>Rename an existing movie</td>
    </tr>
    <tr>
      <td><code>/delete_file</code></td>
      <td>Delete a stored movie</td>
    </tr>
    <tr>
      <td><code>/get_movie_link</code></td>
      <td>Generate a shareable access link for a specific movie</td>
    </tr>
    <tr>
      <td><code>/health</code></td>
      <td>Show bot uptime, memory usage, and CPU statistics</td>
    </tr>
    <tr>
      <td><code>/stats</code></td>
      <td>Display total number of uploaded movies and unique users</td>
    </tr>
    <tr>
      <td><code>/announce</code></td>
      <td>Send a broadcast message to all users (admin-only, with rate-limiting)</td>
    </tr>
  </tbody>
</table>

<h2>⚙️ Tech Stack</h2>
<ul>
  <li><strong>Language:</strong> Python</li>
  <li><strong>Framework:</strong> Flask</li>
  <li><strong>Database:</strong> MongoDB Atlas</li>
  <li><strong>Hosting:</strong> Render</li>
  <li><strong>Logging:</strong> Discord Webhooks (Blue, Green, and Red embeds for actions)</li>
</ul>