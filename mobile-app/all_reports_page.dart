import 'package:flutter/material.dart';
import 'report_store.dart';

class AllReportsPage extends StatefulWidget {
	const AllReportsPage({super.key});

	@override
	State<AllReportsPage> createState() => _AllReportsPageState();
}

class _AllReportsPageState extends State<AllReportsPage> {
	String _category = 'All';
	int _minSeverity = 1;

	@override
	void initState() {
		super.initState();
		reportStore.fetchReports();
	}

	@override
	Widget build(BuildContext context) {
		return Scaffold(
			appBar: AppBar(title: const Text('Report History')),
			body: Padding(
				padding: const EdgeInsets.all(16),
				child: Column(
					children: [
						Row(
							children: [
								Expanded(
									child: DropdownButtonFormField<String>(
										value: _category,
										items: const [
											DropdownMenuItem(value: 'All', child: Text('All Categories')),
											DropdownMenuItem(value: 'General', child: Text('General')),
											DropdownMenuItem(value: 'Road', child: Text('Road')),
											DropdownMenuItem(value: 'Sanitation', child: Text('Sanitation')),
											DropdownMenuItem(value: 'Safety', child: Text('Safety')),
											DropdownMenuItem(value: 'Waste', child: Text('Waste')),
											DropdownMenuItem(value: 'Water', child: Text('Water')),
											DropdownMenuItem(value: 'Electricity', child: Text('Electricity')),
											DropdownMenuItem(value: 'Environment', child: Text('Environment')),
										],
										onChanged: (v) => setState(() => _category = v ?? 'All'),
									),
								),
								const SizedBox(width: 12),
								Expanded(
									child: Column(
										crossAxisAlignment: CrossAxisAlignment.start,
										children: [
											const Text('Severity'),
											Slider(
												min: 1,
												max: 5,
												divisions: 4,
												value: _minSeverity.toDouble(),
												label: _minSeverity.toString(),
												onChanged: (v) => setState(() => _minSeverity = v.round()),
											),
										],
									),
								),
							],
						),
						const SizedBox(height: 12),
						Expanded(
							child: ValueListenableBuilder<List<ReportItem>>(
								valueListenable: reportStore,
								builder: (context, items, _) {
									final filtered = items.where((r) {
										final catOk = _category == 'All' || r.category == _category;
										final sevOk = r.severity >= _minSeverity;
										return catOk && sevOk;
									}).toList();
									if (filtered.isEmpty) return const Center(child: Text('No reports'));
									return ListView.separated(
										itemCount: filtered.length,
										separatorBuilder: (_, __) => const Divider(height: 1),
										itemBuilder: (context, index) {
											final r = filtered[index];
											return ListTile(
												leading: r.imageFile != null 
													? Image.file(r.imageFile!, width: 48, height: 48, fit: BoxFit.cover) 
													: r.imageUrl != null
														? Image.network(r.imageUrl!, width: 48, height: 48, fit: BoxFit.cover)
														: CircleAvatar(child: Text(r.category.characters.first)),
												title: Text(r.title),
												subtitle: Text('${r.category} • Sev ${r.severity}'),
												trailing: Column(
													mainAxisAlignment: MainAxisAlignment.center,
													crossAxisAlignment: CrossAxisAlignment.end,
													children: [
														Container(
															padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
															decoration: BoxDecoration(
																color: r.status == 'Resolved' ? Colors.green.withOpacity(0.1) : Colors.orange.withOpacity(0.1),
																borderRadius: BorderRadius.circular(12),
																border: Border.all(
																	color: r.status == 'Resolved' ? Colors.green : Colors.orange,
																),
															),
															child: Text(
																r.status,
																style: TextStyle(
																	fontSize: 12,
																	fontWeight: FontWeight.bold,
																	color: r.status == 'Resolved' ? Colors.green : Colors.orange,
																),
															),
														),
													],
												),
												onTap: () {},
											);
										},
									);
								},
								),
						),
					],
				),
			),
		);
	}
}
