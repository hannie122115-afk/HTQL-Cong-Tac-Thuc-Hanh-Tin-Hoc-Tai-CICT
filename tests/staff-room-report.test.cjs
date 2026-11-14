const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../static/js/staff/room-detail.js'), 'utf8');

function setup() {
  function element() {
    const handlers = {};
    const classes = new Set();
    return {
      checked: false, indeterminate: false, value: '', textContent: '',
      classList: { add: v => classes.add(v), remove: v => classes.delete(v), contains: v => classes.has(v) },
      addEventListener: (name, fn) => { handlers[name] = fn; },
      emit: (name, event = {}) => handlers[name](event),
      focus() {},
    };
  }
  const nodes = Object.fromEntries([
    'computer-report', 'computer-report-form', 'report-computers-btn', 'report-select-all',
    'report-selected-count', 'cancel-computer-report', 'popup-cancel-confirm',
    'popup-cancel-no', 'popup-cancel-yes', 'popup-error', 'popup-error-message', 'popup-error-close',
    'new-status', 'common-report-fields', 'individual-report-fields', 'machine-details-json',
  ].map(id => [id, element()]));
  const machines = [element(), element(), element()];
  machines.forEach((machine, index) => { machine.value = `PC0${index + 1}`; });
  const modes = [element(), element()];
  modes[0].value = 'common'; modes[0].checked = true;
  modes[1].value = 'individual';
  const rows = machines.map(machine => {
    const row = element();
    row.dataset = {machineId: machine.value};
    row.description = element(); row.status = element();
    row.querySelectorAll = () => [row.description, row.status];
    row.querySelector = selector => selector === '.machine-description' ? row.description : row.status;
    return row;
  });
  nodes['new-status'].value = '1';
  const status = element();
  const form = nodes['computer-report-form'];
  form.querySelectorAll = selector => selector === "[name='computer_ids']" ? machines : selector === "[name='report_mode']" ? modes : rows;
  form.querySelector = () => status;
  form.reset = () => {
    machines.forEach(m => { m.checked = false; }); status.value = '';
    modes[0].checked = true; modes[1].checked = false;
    rows.forEach(row => { row.description.value = ''; row.status.value = ''; });
    nodes['new-status'].value = '';
  };
  vm.runInNewContext(source, { document: { getElementById: id => nodes[id] } });
  const submit = () => {
    const event = { prevented: false, preventDefault() { this.prevented = true; } };
    form.emit('submit', event);
    return event.prevented;
  };
  const setMode = value => {
    modes.forEach(mode => {mode.checked = mode.value === value;});
    modes[0].emit('change');
  };
  return { nodes, machines, status, submit, rows, setMode };
}

test('common button opens picker; select all and partial selection update count', () => {
  const { nodes, machines } = setup();
  nodes['report-computers-btn'].emit('click');
  assert.equal(nodes['computer-report'].classList.contains('show'), true);
  nodes['report-select-all'].checked = true;
  nodes['report-select-all'].emit('change');
  assert.equal(machines.every(m => m.checked), true);
  assert.match(nodes['report-selected-count'].textContent, /3/);
  machines[0].checked = false;
  machines[0].emit('change');
  assert.equal(nodes['report-select-all'].indeterminate, true);
  assert.equal(nodes['report-select-all'].checked, false);
  assert.match(nodes['report-selected-count'].textContent, /2/);
});

test('requires selection and content; allows several selected machines in one submission', () => {
  const { machines, status, submit } = setup();
  status.value = 'Issue';
  assert.equal(submit(), true);
  machines[0].checked = machines[1].checked = true;
  status.value = '  ';
  assert.equal(submit(), true);
  status.value = 'Shared issue';
  assert.equal(submit(), false);
});

test('cancel confirmation clears selected machines, count and report content', () => {
  const { nodes, machines, status } = setup();
  nodes['report-computers-btn'].emit('click');
  machines[0].checked = true;
  status.value = 'Issue';
  nodes['cancel-computer-report'].emit('click');
  assert.equal(nodes['popup-cancel-confirm'].classList.contains('show'), true);
  nodes['popup-cancel-yes'].emit('click');
  assert.equal(machines.some(m => m.checked), false);
  assert.equal(status.value, '');
  assert.equal(nodes['report-select-all'].indeterminate, false);
  assert.match(nodes['report-selected-count'].textContent, /0/);
  assert.equal(nodes['computer-report'].classList.contains('show'), false);
});

test('individual mode requires every selected description/status and serializes only selected machines', () => {
  const { nodes, machines, rows, setMode, submit } = setup();
  machines[0].checked = machines[1].checked = true;
  setMode('individual');
  assert.equal(nodes['common-report-fields'].hidden, true);
  assert.equal(rows[0].hidden, false);
  assert.equal(rows[2].hidden, true);
  assert.equal(submit(), true);
  rows[0].description.value = 'Keyboard broken'; rows[0].status.value = '0';
  rows[1].description.value = 'Cleaning'; rows[1].status.value = '3';
  assert.equal(submit(), false);
  assert.deepEqual(JSON.parse(nodes['machine-details-json'].value), [
    {computer_id: 'PC01', description: 'Keyboard broken', status: 0},
    {computer_id: 'PC02', description: 'Cleaning', status: 3},
  ]);
  machines[1].checked = false;
  machines[1].emit('change');
  assert.equal(rows[1].hidden, true);
  assert.equal(rows[1].description.disabled, true);
  assert.equal(submit(), false);
  assert.equal(JSON.parse(nodes['machine-details-json'].value).length, 1);
  setMode('common');
  setMode('individual');
  assert.equal(rows[0].description.value, 'Keyboard broken');
});
