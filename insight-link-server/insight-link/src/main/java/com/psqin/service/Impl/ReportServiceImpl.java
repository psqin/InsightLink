package com.psqin.service.Impl;

import com.psqin.mapper.*;
import com.psqin.service.ReportService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ReportServiceImpl implements ReportService {

    @Autowired private UserMapper userMapper;
    @Autowired private StudentMapper studentMapper;
    @Autowired private TeacherMapper teacherMapper;
    @Autowired private UniversityMapper universityMapper;
    @Autowired private SysDeptMapper sysDeptMapper;
    @Autowired private TsGuidanceMapper tsGuidanceMapper;
    @Autowired private StuMaterialMapper stuMaterialMapper;
    @Autowired private StuEvalMapper stuEvalMapper;
    @Autowired private NoticeMapper noticeMapper;

    /**
     * 统计总人数及管理员、导师、学生的分布数量
     * @return
     */
    @Override
    public Map<String, Object> overview() {
        Map<String, Object> data = new LinkedHashMap<>();

        Map<String, Object> users = new LinkedHashMap<>();
        Integer usersTotal = userMapper.countAll();
        Integer admins = userMapper.countByRole(1);
        Integer teachers = userMapper.countByRole(2);
        Integer studentsUser = userMapper.countByRole(3);
        users.put("total", usersTotal);
        users.put("admins", admins);
        users.put("teachers", teachers);
        users.put("students", studentsUser);
        data.put("users", users);

        Map<String, Object> schools = new LinkedHashMap<>();
        schools.put("universities", universityMapper.countAll());
        schools.put("colleges", sysDeptMapper.countByDeptType(1));
        schools.put("majors", sysDeptMapper.countByDeptType(2));
        schools.put("classes", sysDeptMapper.countByDeptType(3));
        data.put("schools", schools);

        Map<String, Object> bindings = new LinkedHashMap<>();
        Integer bindingsTotal = tsGuidanceMapper.countAll();
        bindings.put("total", bindingsTotal);
        data.put("bindings", bindings);

        Map<String, Object> materials = new LinkedHashMap<>();
        Integer materialsTotal = stuMaterialMapper.countAll();
        Integer typePlan = stuMaterialMapper.countByType(1);
        Integer typeReport = stuMaterialMapper.countByType(2);
        Integer typeSummary = stuMaterialMapper.countByType(3);
        materials.put("total", materialsTotal);
        materials.put("typePlan", typePlan);
        materials.put("typeReport", typeReport);
        materials.put("typeSummary", typeSummary);
        data.put("materials", materials);

        Map<String, Object> evaluations = new LinkedHashMap<>();
        Integer evalTotal = stuEvalMapper.countAll();
        evaluations.put("total", evalTotal);
        BigDecimal avgScore = stuEvalMapper.avgScore();
        evaluations.put("avgScore", avgScore == null ? BigDecimal.ZERO : avgScore.setScale(2, RoundingMode.HALF_UP));
        data.put("evaluations", evaluations);

        Map<String, Object> notices = new LinkedHashMap<>();
        Integer noticesSystem = noticeMapper.countByType(1);
        Integer noticesTeacher = noticeMapper.countByType(2);
        notices.put("system", noticesSystem);
        notices.put("teacher", noticesTeacher);
        data.put("notices", notices);

        Map<String, Object> rates = new LinkedHashMap<>();

        Map<String, Object> userRoleRate = new LinkedHashMap<>();
        userRoleRate.put("admins", percent(admins, usersTotal));
        userRoleRate.put("teachers", percent(teachers, usersTotal));
        userRoleRate.put("students", percent(studentsUser, usersTotal));
        rates.put("userRoleRate", userRoleRate);

        Map<String, Object> materialTypeRate = new LinkedHashMap<>();
        materialTypeRate.put("typePlan", percent(typePlan, materialsTotal));
        materialTypeRate.put("typeReport", percent(typeReport, materialsTotal));
        materialTypeRate.put("typeSummary", percent(typeSummary, materialsTotal));
        rates.put("materialTypeRate", materialTypeRate);

        Map<String, Object> evaluatedRate = new LinkedHashMap<>();
        evaluatedRate.put("evaluatedMaterials", evalTotal);
        evaluatedRate.put("evaluatedPercent", percent(evalTotal, materialsTotal));
        Integer unEvaluated = safeSub(materialsTotal, evalTotal);
        evaluatedRate.put("unEvaluatedMaterials", unEvaluated);
        evaluatedRate.put("unEvaluatedPercent", percent(unEvaluated, materialsTotal));
        rates.put("evaluatedRate", evaluatedRate);

        Map<String, Object> bindRate = new LinkedHashMap<>();
        Integer students = studentMapper.countAll();
        bindRate.put("studentsTotal", students);
        bindRate.put("boundStudents", bindingsTotal);
        bindRate.put("boundPercent", percent(bindingsTotal, students));
        bindRate.put("unboundStudents", safeSub(students, bindingsTotal));
        bindRate.put("unboundPercent", percent(safeSub(students, bindingsTotal), students));
        rates.put("bindRate", bindRate);

        Map<String, Object> noticeTypeRate = new LinkedHashMap<>();
        Integer noticesTotal = safeAdd(noticesSystem, noticesTeacher);
        noticeTypeRate.put("systemPercent", percent(noticesSystem, noticesTotal));
        noticeTypeRate.put("teacherPercent", percent(noticesTeacher, noticesTotal));
        rates.put("noticeTypeRate", noticeTypeRate);

        data.put("rates", rates);

        return data;
    }

    @Override
    public Map<String, Object> trend(Integer days) {
        int d = days == null ? 30 : days;
        if (d < 1) d = 1;
        if (d > 90) d = 90;
        LocalDate end = LocalDate.now();
        LocalDate start = end.minusDays(d - 1);
        LocalDateTime startTime = start.atStartOfDay();
        List<String> labels = new ArrayList<>();
        for (LocalDate cur = start; !cur.isAfter(end); cur = cur.plusDays(1)) {
            labels.add(cur.toString());
        }
        Map<String, List<Integer>> series = new LinkedHashMap<>();
        series.put("usersTotal", alignDaily(labels, userMapper.listDailyCount(startTime)));
        series.put("admins", alignDaily(labels, userMapper.listDailyCountByRole(1, startTime)));
        series.put("teachers", alignDaily(labels, userMapper.listDailyCountByRole(2, startTime)));
        series.put("students", alignDaily(labels, userMapper.listDailyCountByRole(3, startTime)));
        series.put("materialsTotal", alignDaily(labels, stuMaterialMapper.listDailyCount(startTime)));
        series.put("typePlan", alignDaily(labels, stuMaterialMapper.listDailyCountByType(1, startTime)));
        series.put("typeReport", alignDaily(labels, stuMaterialMapper.listDailyCountByType(2, startTime)));
        series.put("typeSummary", alignDaily(labels, stuMaterialMapper.listDailyCountByType(3, startTime)));
        series.put("evaluationsTotal", alignDaily(labels, stuEvalMapper.listDailyCount(startTime)));
        series.put("noticesSystem", alignDaily(labels, noticeMapper.listDailyCountByType(1, startTime)));
        series.put("noticesTeacher", alignDaily(labels, noticeMapper.listDailyCountByType(2, startTime)));
        series.put("bindingsTotal", alignDaily(labels, tsGuidanceMapper.listDailyCount(startTime)));
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("labels", labels);
        data.put("series", series);
        return data;
    }

    private List<Integer> alignDaily(List<String> labels, List<com.psqin.domain.vo.DailyCountVO> records) {
        Map<String, Integer> map = records == null ? Collections.emptyMap() :
                records.stream().collect(Collectors.toMap(com.psqin.domain.vo.DailyCountVO::getDay, com.psqin.domain.vo.DailyCountVO::getCount));
        List<Integer> values = new ArrayList<>(labels.size());
        for (String day : labels) {
            values.add(map.getOrDefault(day, 0));
        }
        return values;
    }

    /**
     * 统计各个大学的学生和导师分布情况
     * @return
     */
    @Override
    public Map<String, Object> distributionSchool() {
        Map<String, Object> data = new LinkedHashMap<>();
        List<com.psqin.domain.vo.NameCountVO> studentsByUniversity = studentMapper.listCountByUniversity();
        List<com.psqin.domain.vo.NameCountVO> teachersByUniversity = teacherMapper.listCountByUniversity();
        fillPercent(studentsByUniversity);
        fillPercent(teachersByUniversity);
        data.put("studentsByUniversity", studentsByUniversity);
        data.put("teachersByUniversity", teachersByUniversity);
        return data;
    }

    //自动计算一组数据的总和
    private void fillPercent(List<com.psqin.domain.vo.NameCountVO> list) {
        if (list == null || list.isEmpty()) return;
        int total = list.stream().map(com.psqin.domain.vo.NameCountVO::getCount).filter(java.util.Objects::nonNull).mapToInt(Integer::intValue).sum();
        for (com.psqin.domain.vo.NameCountVO vo : list) {
            vo.setPercent(percent(vo.getCount(), total));
        }
    }

    //百分比计算工具函数
    private BigDecimal percent(Integer numerator, Integer denominator) {
        int d = denominator == null ? 0 : denominator;
        int n = numerator == null ? 0 : numerator;
        if (d <= 0) return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        return BigDecimal.valueOf(n)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(d), 2, RoundingMode.HALF_UP);
    }

    private Integer safeAdd(Integer a, Integer b) {
        return (a == null ? 0 : a) + (b == null ? 0 : b);
    }

    private Integer safeSub(Integer a, Integer b) {
        int x = a == null ? 0 : a;
        int y = b == null ? 0 : b;
        int r = x - y;
        return Math.max(r, 0);
    }
}
