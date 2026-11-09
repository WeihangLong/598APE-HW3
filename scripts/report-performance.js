const fs = require('node:fs');
const path = require('node:path');

module.exports = async ({github, context, core}) => {
  const directory = process.env.RESULTS_DIR;
  const metadata = JSON.parse(fs.readFileSync(path.join(directory, 'environment.json'), 'utf8'));
  const summary = fs.readFileSync(path.join(directory, 'summary.md'), 'utf8');
  const {owner, repo} = context.repo;
  let pull = context.payload.pull_request;

  // Manual runs also report to the open PR for the selected experiment.
  if (!pull) {
    const {data} = await github.rest.pulls.list({
      owner, repo, state: 'open', base: 'main',
      head: `${owner}:${process.env.CANDIDATE_BRANCH}`, per_page: 100,
    });
    if (data.length !== 1) {
      core.notice('No unique open PR for this branch; results remain in the job summary.');
      return;
    }
    pull = data[0];
  }

  const {data: current} = await github.rest.pulls.get({owner, repo, pull_number: pull.number});
  if (current.state !== 'open' || current.head.sha !== metadata.refs.candidate) {
    core.notice('The PR closed or changed during the benchmark; skipping stale results.');
    return;
  }

  const marker = '<!-- hw3-performance-comparison -->';
  const runUrl = `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}`;
  const body = `${marker}\n${summary}\n[Benchmark run and raw results](${runUrl})`;
  const comments = await github.paginate(github.rest.issues.listComments, {
    owner, repo, issue_number: pull.number, per_page: 100,
  });
  const existing = comments.find(comment =>
    comment.user?.login === 'github-actions[bot]' && comment.body?.includes(marker));
  if (existing) {
    await github.rest.issues.updateComment({owner, repo, comment_id: existing.id, body});
  } else {
    await github.rest.issues.createComment({owner, repo, issue_number: pull.number, body});
  }
};
