use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_is_test_file(c: &mut Criterion) {
    let samples = [
        "test_foo.py",
        "foo_test.py",
        "regular.py",
        "test_",
        "_test.py",
    ];

    c.bench_function("is_test_file_variants", |b| {
        b.iter(|| {
            for s in &samples {
                let _ = black_box(s.starts_with("test_") || s.ends_with("_test.py"));
            }
        });
    });
}

fn bench_group_tests(c: &mut Criterion) {
    use std::collections::HashMap;
    let mut tests = Vec::new();
    for i in 0..1000 {
        let file = format!("test_{}.py", i % 50);
        tests.push(oxytest_core::types::TestItem::new_no_args(
            file, format!("test_func_{}", i), (i % 20) as u32,
        ));
    }

    c.bench_function("group_1000_tests_by_path", |b| {
        b.iter(|| {
            let mut grouped: HashMap<String, Vec<_>> = HashMap::new();
            for test in black_box(&tests) {
                grouped.entry(black_box(&test.path).clone()).or_default().push(test.clone());
            }
            black_box(grouped);
        });
    });
}

criterion_group!(benches, bench_is_test_file, bench_group_tests);
criterion_main!(benches);
